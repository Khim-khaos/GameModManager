Руководство пользователя GameModManager
GameModManager — это приложение для управления модами для игр из Steam, использующее SteamCMD для загрузки модов из Steam Workshop. Автор: Khim_Khaosow.
Установка

Установите Python 3.8+.
Скачайте SteamCMD с официального сайта Valve.
Клонируйте репозиторий:git clone <ссылка_на_репозиторий>
cd GameModManager


Установите зависимости:pip install -r requirements.txt


Запустите приложение:python src/main.py



Основные функции
1. Управление играми

Добавление игры: Укажите название, App ID, путь к .exe и папку модов.
Редактирование игры: Измените параметры существующей игры.
Запуск игры: Запустите игру прямо из интерфейса.

2. Управление модами

Загрузка модов: Используйте встроенный браузер Steam Workshop для выбора модов.
Очередь загрузки: Добавляйте моды в очередь и управляйте порядком (drag-and-drop).
Зависимости: Автоматическое обнаружение и установка зависимостей модов.
Включение/отключение модов: Временно отключайте моды без удаления.
Информация о моде: Просматривайте название, описание и зависимости мода.
Проверка целостности: Проверка корректности загруженных файлов модов.

3. Интерфейс

Темы: Выберите светлую или темную тему.
Фон: Установите собственное фоновое изображение.
Прозрачность: Настройте прозрачность интерфейса.
Шрифты: Измените размер шрифта.
Локализация: Поддержка русского и английского языков.

4. Логи и консоль

Консоль SteamCMD: Просматривайте вывод SteamCMD во время загрузки модов.
Логи программы: Фильтруйте логи по уровням (INFO, ERROR, DEBUG).

Настройки

Укажите путь к steamcmd.exe.
Выберите язык, тему, фон, прозрачность и размер шрифта.
Сохраняйте положение и размер окна.

Сборка исполняемого файла

Установите pyinstaller:pip install pyinstaller


Выполните сборку:python build_exe.py


Найдите исполняемый файл в dist/GameModManager/.

Устранение неполадок

SteamCMD не найден: Убедитесь, что путь к steamcmd.exe указан в настройках.
Моды не загружаются: Проверьте подключение к интернету и правильность App ID игры.
Ошибки в логах: Используйте фильтр логов для поиска проблем.

Лицензия
MIT License, (c) 2025 Khim_Khaosow
