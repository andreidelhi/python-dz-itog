# Python Сервер Задач

HTTP API для управления списком задач.

## Запуск

```powershell
python server.py
```

Или на Windows:

```powershell
.\start_server.bat
```

## API

- `GET /tasks` - получить все задачи
- `POST /tasks` - создать задачу
- `POST /tasks/{id}/complete` - отметить задачу выполненной

Пример запроса на создание задачи:

```json
{
  "title": "Купить молоко",
  "priority": "normal"
}
```

После каждого изменения сервер сохраняет задачи в `tasks.txt`, а при следующем запуске восстанавливает их из этого файла.
