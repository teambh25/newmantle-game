FROM python:slim AS base
WORKDIR /src
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

FROM base AS prod
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]

FROM base AS test
COPY requirements-test.txt requirements-test.txt
RUN pip install -r requirements-test.txt
ENTRYPOINT ["python", "-m", "pytest"]