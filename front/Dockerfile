FROM python:3.12-slim

WORKDIR /app
COPY ./front/requirements.txt .
RUN pip install -r requirements.txt
COPY ../assets ../assets
COPY ./front/streamlit_app.py ./streamlit_app.py


EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py"]