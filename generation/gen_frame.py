# pillow-9.1.0
from demotivator import Demotivator

IMG1 = '../audio/default/img1.jpg'
IMG2 = '../audio/default/img2.jpg'
DIR = "../temp_img/"
SEGMENTS = [(' Здравствуйте.', 'SPEAKER_00', 0.031, 5.06), ('Здравствуйте.', 'SPEAKER_00', 5.08, 6.182),
                ('Меня зовут Вероника.', 'SPEAKER_00', 6.202, 7.404),
                ('Это федеральный юридический центр.', 'SPEAKER_00', 7.424, 8.646),
                ('Вы интересовались списанием кредита.', 'SPEAKER_00', 8.666, 10.73),
                ('Хотели проконсультироваться, верно?', 'SPEAKER_00', 10.75, 18.864),
                ('Вас не слышно.', 'SPEAKER_01', 18.884, 19.284), ('Чё хотела?', 'SPEAKER_01', 19.304, 21.088),
                ('Процедурой банкротства интересовались?', 'SPEAKER_00', 21.108, 23.191),
                ('Вы хотели консультацию получить?', 'SPEAKER_00', 23.211, 24.233),
                (' Да послушайте, идите все нахуй, меня так заебали уже.', 'SPEAKER_01', 26.947, 30.515),
                ('С утра еще звонят, козлы ебаные пляшут.', 'SPEAKER_01', 30.576, 34.003)]


def create_img_rec(segments, img1, img2, index):
    if index == len(segments):
        return
    text = segments[index][0].upper()
    demotivator = Demotivator(text)
    # АНАКОНДА
    #
    if segments[index][1] == "SPEAKER_00":
        demotivator.create(file=img1, result_filename=f"{DIR}dem{index}.jpg", fill_color='black',
                           font_name='IslandOfTreasure-Regular.otf', watermark='АНАКОНДА', arrange=False)
        create_img_rec(segments, f"{DIR}dem{index}.jpg", img2, index + 1)
    else:
        demotivator.create(file=img2, result_filename=f"{DIR}dem{index}.jpg", fill_color='black',
                           font_name='IslandOfTreasure-Regular.otf', watermark='АНАКОНДА', arrange=False)
        create_img_rec(segments, img1, f"{DIR}dem{index}.jpg", index + 1)


def create_demotivator(segments=SEGMENTS, img1=IMG1, img2=IMG2):
    # Цель функции: создать кортеж фотографий для фрагментов видео-демотиватора

    # segments - список сегментов, которые нужно обработать
    # img1 - путь к первой фотографии - фотография для первого спикера
    # img2 - путь ко второй фотографии - фотография для второго спикера
    # впоследствии будут заменены на сгенерированные по тексту диалога

    create_img_rec(segments, img1, img2, 0)


if __name__ == "__main__":
    create_demotivator()
