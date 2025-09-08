FROM python:slim
WORKDIR /src
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]