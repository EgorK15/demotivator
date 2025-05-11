import whisperx
from mutagen.mp3 import MP3
from dotenv import load_dotenv, find_dotenv
from huggingface_hub import login
import os
import argparse

# Загрузка переменных окружения из файла .env
load_dotenv(find_dotenv())

YOUR_HF_TOKEN = os.getenv("HF_TOKEN")

audio_file = "audio/audio1.mp3"
batch_size = 16  # Reduce if low on GPU mem
compute_type = "int8"  # Change to "int8" if low on GPU mem (may reduce accuracy)
device = "cpu"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Transcribe and diarize an audio file using WhisperX.")

    # Add arguments for audio_file, batch_size, compute_type, and device
    parser.add_argument("--audio_file", type=str, help="Path to the input MP3 audio file.", default=audio_file)
    parser.add_argument("--batch_size", type=int, help="Batch size for inference.", default=batch_size)
    parser.add_argument("--compute_type", type=str, choices=["int8", "float16"],
                        help="Compute type for model inference.", default=compute_type)
    parser.add_argument("--device", type=str, choices=["cpu", "cuda"], help="Device to use for computation.",
                        default=device)

    return parser.parse_args()


def transcribe_and_diarize_audio(audio_file=audio_file, batch_size=batch_size, compute_type=compute_type, device=device):
    model = whisperx.load_model("large-v2", "cpu", compute_type=compute_type)
    # YOUR_HF_TOKEN = "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"
    login(token=YOUR_HF_TOKEN)
    audio = whisperx.load_audio(audio_file)
    result = model.transcribe(audio, batch_size=batch_size)

    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

    print(result["segments"])  # after alignment

    # diarize_model = Model.from_pretrained('pyannote/segmentation-3.0',use_auth_token=YOUR_HF_TOKEN)
    diarize_model = whisperx.diarize.DiarizationPipeline(use_auth_token=YOUR_HF_TOKEN, device=device)

    # add min/max number of speakers if known
    diarize_segments = diarize_model(audio, num_speakers=2)

    result = whisperx.assign_word_speakers(diarize_segments, result)

    segments = [(segment["text"], segment["speaker"], segment["start"], segment["end"]) for segment in
                result["segments"]]

    return segments


if __name__ == "__main__":
    args = parse_arguments()

    mp3_obj = MP3(args.audio_file)
    diarize_segments = transcribe_and_diarize_audio(audio_file=args.audio_file, batch_size=args.batch_size,
                                                    compute_type=args.compute_type, device=args.device)
    print(diarize_segments)
