FROM continuumio/miniconda3:latest

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PICK_LTL_CONFIG_DIR=/config \
    PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN conda config --add channels conda-forge \
    && conda config --set channel_priority strict \
    && conda install -y python=3.12 pip spot \
    && pip install gunicorn \
    && pip install -e . \
    && conda clean -afy

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "pick_ltl.app:app"]

