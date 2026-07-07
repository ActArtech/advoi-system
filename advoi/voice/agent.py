"""Stage 1 Pipecat voice agent — LiveKit transport + OpenAI STT/LLM/TTS."""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv(override=True)

from loguru import logger  # noqa: E402

from advoi.llm.openrouter import resolve_llm_credentials  # noqa: E402
from advoi.memory import MemoryRouter  # noqa: E402
from advoi.voice.livekit_env import internal_livekit_url  # noqa: E402
from advoi.voice.frame_dispatch import handle_frame_message  # noqa: E402
from advoi.voice.memory_hooks import build_memory_processor  # noqa: E402
from advoi.voice.prompts import build_system_instruction  # noqa: E402
from advoi.voice.tokens import default_room_name, mint_room_token  # noqa: E402


async def _memory_context() -> str:
    router = MemoryRouter()
    recall = await router.recall(session_id="voice-main", query="ADVoi portfolio executive context")
    chunks: list[str] = []
    for item in recall.strategic + recall.operational + recall.ephemeral:
        text = item.get("text") or item.get("content") or item.get("summary")
        if text:
            chunks.append(str(text))
    return "\n".join(chunks[:6])


async def run_agent() -> None:
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.frames.frames import TTSSpeakFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.worker import PipelineParams, PipelineWorker
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import (
        LLMContextAggregatorPair,
        LLMUserAggregatorParams,
    )
    from pipecat.services.openai.llm import OpenAILLMService
    from pipecat.services.openai.stt import OpenAISTTService
    from pipecat.services.openai.tts import OpenAITTSService
    from pipecat.transports.livekit.transport import LiveKitParams, LiveKitTransport
    from pipecat.workers.runner import WorkerRunner

    creds = resolve_llm_credentials()

    livekit_url = internal_livekit_url()

    room_name = default_room_name()
    bot_token = mint_room_token(
        room_name=room_name,
        identity=os.getenv("LIVEKIT_BOT_IDENTITY", "advoi-bot"),
        name="ADVoi",
    )

    session_id = os.getenv("ADVOI_VOICE_SESSION_ID", "voice-main")
    memory_context = await _memory_context()
    system_instruction = build_system_instruction(memory_context=memory_context)
    memory_in = build_memory_processor(session_id)
    memory_out = build_memory_processor(session_id)

    transport = LiveKitTransport(
        url=livekit_url,
        token=bot_token,
        room_name=room_name,
        params=LiveKitParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    )

    stt = OpenAISTTService(
        api_key=creds.api_key,
        base_url=creds.base_url,
        model=creds.stt_model,
    )
    llm = OpenAILLMService(
        api_key=creds.api_key,
        base_url=creds.base_url,
        model=creds.llm_model,
        settings=OpenAILLMService.Settings(system_instruction=system_instruction),
    )
    tts = OpenAITTSService(
        api_key=creds.api_key,
        base_url=creds.base_url,
        model=creds.tts_model,
        settings=OpenAITTSService.Settings(
            voice=os.getenv("OPENAI_TTS_VOICE", "alloy"),
        ),
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            memory_in,
            user_aggregator,
            llm,
            memory_out,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            audio_out_sample_rate=24000,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        # Keep the bot in the room between sessions (Pipecat default is 300s idle cancel).
        idle_timeout_secs=None,
        cancel_on_idle_timeout=False,
    )

    greeted_participants: set[str] = set()

    async def _greet_participant(participant_id: str) -> None:
        if participant_id in greeted_participants:
            return
        greeted_participants.add(participant_id)
        await asyncio.sleep(0.5)
        logger.info("Greeting participant {}", participant_id)
        await worker.queue_frame(
            TTSSpeakFrame("Hi — I'm ADVoi. What should we look at in the portfolio today?")
        )

    @transport.event_handler("on_participant_connected")
    async def on_participant_connected(transport, participant_id):  # noqa: ARG001
        await _greet_participant(participant_id)

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant_id):  # noqa: ARG001
        await _greet_participant(participant_id)

    @transport.event_handler("on_data_received")
    async def on_data_received(transport, data, participant_id):  # noqa: ARG001
        spoken = await handle_frame_message(data)
        if spoken:
            logger.info("Frame data from {} — speaking response", participant_id)
            await worker.queue_frame(TTSSpeakFrame(spoken))

    runner = WorkerRunner()
    await runner.add_workers(worker)
    logger.info(
        "ADVoi voice agent joining room {} (llm_provider={} model={})",
        room_name,
        creds.provider,
        creds.llm_model,
    )
    await runner.run()


def main() -> None:
    logger.remove()
    logger.add(sys.stderr, level=os.getenv("ADVOI_LOG_LEVEL", "INFO"))
    asyncio.run(run_agent())


if __name__ == "__main__":
    main()