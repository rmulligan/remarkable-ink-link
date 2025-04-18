FROM python:3.10-slim

WORKDIR /app

RUN pip install --upgrade pip && pip install poetry

COPY . /app

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

CMD ["poetry", "run", "inklink"]