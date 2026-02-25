# GameModManager

A comprehensive Python-based application for managing game mods with Steam Workshop integration. The application provides a user-friendly interface for installing, enabling, disabling, and organizing mods for multiple games.

## Features

- **Multi-Game Support**: Manage mods for multiple games simultaneously
- **Steam Workshop Integration**: Browse and install mods directly from Steam Workshop
- **Mod Management**: Enable, disable, and organize mods with ease
- **Game Launching**: Launch games directly from the application
- **Multi-Language Support**: Interface available in multiple languages
- **Mod Dependencies**: Automatic handling of mod dependencies
- **Archive System**: Disabled mods are automatically moved to an archive folder
- **Real-time Updates**: Live monitoring of game processes

## Installation

### Prerequisites

- Python 3.8 or higher
- Steam client (for Steam Workshop integration)
- Games with mod support

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Khim-khaos/GameModManager.git
cd GameModManager
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Usage

### Adding Games

1. Click "Add Game" in the main interface
2. Enter game information:
   - Game name
   - Steam App ID
   - Path to executable file
   - Path to mods folder
3. The application will validate the paths and add the game to your library

### Managing Mods

#### From Local Files
- Mods are automatically detected in your game's mods folder
- Enable/disable mods with a single click
- Disabled mods are moved to an "archive" subfolder

#### From Steam Workshop
1. Switch to the "Browser" tab
2. Browse or search for mods on Steam Workshop
3. Install mods directly to your game
4. Manage dependencies automatically

### Launching Games

- Select your game from the dropdown menu
- Click "Launch Game" to start the game
- The application monitors the game process and updates the interface accordingly

### Settings

Access settings through the menu (File → Settings) to configure:
- SteamCMD path
- Default language
- Application preferences

## Project Structure

```
src/
├── core/                    # Core application logic
│   ├── game_manager.py     # Game management functionality
│   ├── mod_manager.py      # Mod management functionality
│   ├── steam_handler.py    # Steam integration
│   ├── download_manager.py # Download management
│   ├── task_manager.py     # Background task management
│   └── logger.py           # Logging configuration
├── models/                  # Data models
│   ├── game.py            # Game model
│   └── mod.py             # Mod model with dependencies
├── ui/                     # User interface components
│   ├── main_window.py     # Main application window
│   ├── tabs/              # Application tabs
│   │   ├── mods_tab.py    # Mods management tab
│   │   ├── browser_tab.py # Steam Workshop browser
│   │   └── logs_tab.py    # Application logs
│   └── dialogs/           # Dialog windows
│       ├── add_game_dialog.py
│       ├── edit_game_dialog.py
│       └── settings_dialog.py
├── data/                   # Application data
│   ├── games.json         # Game configurations
│   ├── settings.json      # Application settings
│   └── mod_versions.json  # Mod version tracking
└── language/              # Language files
    ├── en.json           # English translations
    └── rus.json          # Russian translations
```

## Dependencies

The application uses the following key dependencies:

- **wxPython**: GUI framework
- **requests**: HTTP requests for Steam API
- **beautifulsoup4**: HTML parsing for Steam Workshop
- **steam**: Steam integration library
- **loguru**: Logging library
- **psutil**: Process management
- **sqlalchemy**: Database ORM

## Development

### Adding New Features

1. Follow the existing MVC pattern
2. Add new functionality to the appropriate core module
3. Create UI components in the tabs or dialogs directories
4. Update language files for multi-language support
5. Write tests for new functionality

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For support and questions:
- Check the project documentation
- Review existing issues
- Create a new issue for bugs or feature requests

---

# GameModManager

Комплексное приложение на Python для управления модами с интеграцией Steam Workshop. Приложение предоставляет удобный интерфейс для установки, включения, отключения и организации модов для нескольких игр.

## Возможности

- **Поддержка нескольких игр**: Управление модами для нескольких игр одновременно
- **Интеграция Steam Workshop**: Просмотр и установка модов напрямую из Steam Workshop
- **Управление модами**: Включение, отключение и организация модов с легкостью
- **Запуск игр**: Запуск игр прямо из приложения
- **Многоязычная поддержка**: Интерфейс доступен на нескольких языках
- **Зависимости модов**: Автоматическая обработка зависимостей модов
- **Система архивации**: Отключенные моды автоматически перемещаются в папку архива
- **Реальное время**: Мониторинг процессов игры в реальном времени

## Установка

### Предварительные требования

- Python 3.8 или выше
- Steam клиент (для интеграции Steam Workshop)
- Игры с поддержкой модов

### Настройка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/Khim-khaos/GameModManager.git
cd GameModManager
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Запустите приложение:
```bash
python main.py
```

## Использование

### Добавление игр

1. Нажмите "Добавить игру" в основном интерфейсе
2. Введите информацию об игре:
   - Название игры
   - Steam App ID
   - Путь к исполняемому файлу
   - Путь к папке модов
3. Приложение проверит пути и добавит игру в вашу библиотеку

### Управление модами

#### Из локальных файлов
- Моды автоматически обнаруживаются в папке модов вашей игры
- Включайте/отключайте моды одним щелчком мыши
- Отключенные моды перемещаются в подпапку "archive"

#### Из Steam Workshop
1. Переключитесь на вкладку "Браузер"
2. Просматривайте или ищите моды в Steam Workshop
3. Устанавливайте моды прямо в вашу игру
4. Автоматическое управление зависимостями

### Запуск игр

- Выберите игру из выпадающего меню
- Нажмите "Запустить игру", чтобы начать игру
- Приложение отслеживает процесс игры и соответствующим образом обновляет интерфейс

### Настройки

Доступ к настройкам через меню (Файл → Настройки) для конфигурации:
- Путь к SteamCMD
- Язык по умолчанию
- Предпочтения приложения

## Структура проекта

```
src/
├── core/                    # Основная логика приложения
│   ├── game_manager.py     # Функциональность управления играми
│   ├── mod_manager.py      # Функциональность управления модами
│   ├── steam_handler.py    # Интеграция со Steam
│   ├── download_manager.py # Управление загрузками
│   ├── task_manager.py     # Управление фоновыми задачами
│   └── logger.py           # Конфигурация логирования
├── models/                  # Модели данных
│   ├── game.py            # Модель игры
│   └── mod.py             # Модель мода с зависимостями
├── ui/                     # Компоненты пользовательского интерфейса
│   ├── main_window.py     # Главное окно приложения
│   ├── tabs/              # Вкладки приложения
│   │   ├── mods_tab.py    # Вкладка управления модами
│   │   ├── browser_tab.py # Браузер Steam Workshop
│   │   └── logs_tab.py    # Журнал приложения
│   └── dialogs/           # Диалоговые окна
│       ├── add_game_dialog.py
│       ├── edit_game_dialog.py
│       └── settings_dialog.py
├── data/                   # Данные приложения
│   ├── games.json         # Конфигурации игр
│   ├── settings.json      # Настройки приложения
│   └── mod_versions.json  # Отслеживание версий модов
└── language/              # Языковые файлы
    ├── en.json           # Английские переводы
    └── rus.json          # Русские переводы
```

## Зависимости

Приложение использует следующие ключевые зависимости:

- **wxPython**: GUI фреймворк
- **requests**: HTTP запросы для Steam API
- **beautifulsoup4**: Парсинг HTML для Steam Workshop
- **steam**: Библиотека интеграции со Steam
- **loguru**: Библиотека логирования
- **psutil**: Управление процессами
- **sqlalchemy**: ORM для баз данных

## Разработка

### Добавление новых функций

1. Следуйте существующему MVC шаблону
2. Добавьте новую функциональность в соответствующий основной модуль
3. Создайте компоненты UI в каталогах tabs или dialogs
4. Обновите языковые файлы для многоязычной поддержки
5. Напишите тесты для новой функциональности

### Вклад в развитие

1. Создайте форк репозитория
2. Создайте ветку функции
3. Внесите свои изменения
4. Добавьте тесты, если применимо
5. Отправьте запрос на включение изменений

## Лицензия

Этот проект лицензирован по лицензии MIT. Подробности см. в файле LICENSE.

## Поддержка

По вопросам поддержки:
- Проверьте документацию проекта
- Просмотрите существующие проблемы
- Создайте новую проблему для ошибок или запросов функций