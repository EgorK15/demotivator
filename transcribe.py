import whisperx
from mutagen.mp3 import MP3
import os
from huggingface_hub import login
from pyannote.audio import Model

print(os.getcwd())
audio_file = r"C:\Users\korsh\PycharmProjects\demotivator\0.mp3"
batch_size = 16 # reduce if low on GPU mem
compute_type = "int8" # change to "int8" if low on GPU mem (may reduce accuracy)
device = "cpu"
model = whisperx.load_model("large-v2", "cpu", compute_type=compute_type)
YOUR_HF_TOKEN = "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"
login(token = YOUR_HF_TOKEN)
audio = whisperx.load_audio(audio_file)
result = model.transcribe(audio, batch_size=batch_size)


model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

print(result["segments"]) # after alignment


#diarize_model = Model.from_pretrained('pyannote/segmentation-3.0',use_auth_token=YOUR_HF_TOKEN)
diarize_model = whisperx.DiarizationPipeline(use_auth_token=YOUR_HF_TOKEN, device=device)

# add min/max number of speakers if known
diarize_segments = diarize_model(audio,num_speakers=2)
# diarize_model(audio, min_speakers=min_speakers, max_speakers=max_speakers)

result = whisperx.assign_word_speakers(diarize_segments, result)
mp3_obj = MP3(audio_file)
print(diarize_segments)

segments = [(segment["text"], segment["speaker"]) for segment in result["segments"]]

print(segments)


print(mp3_obj.info.length)