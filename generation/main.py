import argparse

from generation import gen_frame
from generation import transcribe
from pathlib import Path
from moviepy.editor import *

# Определяем корневую директорию проекта
ROOT_DIR = Path(__file__).resolve().parent
print(f"ROOT_DIR: {ROOT_DIR}")

# Определяем пути к ресурсам
DIR = str(ROOT_DIR) + '/temp_img/dem'
IMG1 = str(ROOT_DIR) + '/resource/1.jpg'
IMG2 = str(ROOT_DIR) + '/resource/2.jpg'
AUDIO = str(ROOT_DIR) + '/resource/1.mp3'
OUTPUT = str(ROOT_DIR) + '/output/1.mp4'

SEGMENTS = [
    ('Здравствуйте.', 'SPEAKER_00', 0.031, 5.06),
    ('Здравствуйте.', 'SPEAKER_00', 5.08, 6.182),
    ('Меня зовут Вероника.', 'SPEAKER_00', 6.202, 7.404),
    ('Это федеральный юридический центр.', 'SPEAKER_00', 7.424, 8.646),
    ('Вы интересовались списанием кредита.', 'SPEAKER_00', 8.666, 10.73),
    ('Хотели проконсультироваться, верно?', 'SPEAKER_00', 10.75, 18.864),
    ('Вас не слышно.', 'SPEAKER_01', 18.884, 19.284),
    ('Чё хотела?', 'SPEAKER_01', 19.304, 21.088),
    ('Процедурой банкротства интересовались?', 'SPEAKER_00', 21.108, 23.191),
    ('Вы хотели консультацию получить?', 'SPEAKER_00', 23.211, 24.233),
    ('Да послушайте, идите все нахuй, меня так заebали уже.', 'SPEAKER_01', 26.947, 30.515),
    ('С утра еще звонят, козлы еbаные пляшут.', 'SPEAKER_01', 30.576, 34.003)
]


def timeline(segments, length_audio):
    """
    Создает временную шкалу для сегментов аудио.

    :param segments: Список сегментов с текстом, спикером и временными метками.
    :return: Список сегментов с обновленными временными метками.
    """
    time = [[f"{DIR}0.jpg", round(segments[1][2], 4)]]
    for i in range(1, len(segments) - 1):
        time.append([f"{DIR}{i}.jpg", round(segments[i + 1][2] - segments[i][2], 4)])
    time.append([f"{DIR}{len(segments) - 1}.jpg", round(length_audio - segments[len(segments) - 1][2], 4)])

    return time


def create_video(audio_file: str = AUDIO, img1: str = IMG1, img2: str = IMG2, result_filename: str = OUTPUT):
    """
    Создает видео-демотиватор на основе аудио и изображений.

    :param audio_file: Путь к аудиофайлу.
    :param img1: Путь к изображению для первого спикера.
    :param img2: Путь к изображению для второго спикера.
    :param result_filename: Имя выходного видеофайла.
    """

    # Получаем сегменты аудио с распознанным текстом и спикерами
    # segments = SEGMENTS
    segments = transcribe.transcribe_and_diarize_audio(audio_file=audio_file, batch_size=16, compute_type="int8",
                                                       device="cpu")

    # Создаем демотиваторы на основе сегментов и изображений
    gen_frame.create_demotivator(segments, img1, img2)

    # Создаем временную шкалу для сегментов
    time = timeline(segments, AudioFileClip(audio_file).duration)

    # Создаем список клипов для каждого сегмента
    clips = []
    for i, (img_path, duration) in enumerate(time):
        clip = ImageClip(img_path).set_duration(duration)
        clips.append(clip)

    # Объединяем клипы в одно видео
    video = concatenate_videoclips(clips, method="compose")

    # Создаем объект аудиофайла и добавляем его к видео
    audio_clip = AudioFileClip(audio_file)
    final_video = video.set_audio(audio_clip)

    # Сохраняем видео в файл
    final_video.write_videofile(result_filename, codec='libx264', audio_codec='aac', temp_audiofile='temp-resource.m4a',
                                remove_temp=True, fps=24)

    # Удаляем временные файлы
    for img_path, _ in time:
        os.remove(img_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio_file", type=str, default=AUDIO)
    parser.add_argument("--img1", type=str, default=IMG1)
    parser.add_argument("--img2", type=str, default=IMG2)
    parser.add_argument("--output", type=str, default=OUTPUT)
    args = parser.parse_args()
    create_video(audio_file=args.audio_file, img1=args.img1, img2=args.img2, result_filename=args.output)
