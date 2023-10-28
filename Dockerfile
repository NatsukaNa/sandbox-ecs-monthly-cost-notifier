FROM python:3.11.6-slim

# pipコマンドをZscaler配下で実行するための証明書設定
ADD ZscalerRootCertificate-2048-SHA256.crt /usr/local/share/ca-certificates/ZscalerRootCertificate-2048-SHA256.crt
ENV REQUESTS_CA_BUNDLE /usr/local/share/ca-certificates/ZscalerRootCertificate-2048-SHA256.crt

# poetryをインストールし、依存関係を解決する
RUN pip install poetry
COPY poetry.lock poetry.lock
COPY pyproject.toml pyproject.toml
RUN poetry config virtualenvs.create false
RUN poetry install

# 実行ファイル配置とデフォルト環境変数を設定する
COPY main.py main.py
ENV MATTERMOST_CHANNEL  "test_natsuka_nakajima"
ENV MATTERMOST_WEBHOOK_URL "https://mattermost.paylab.sh/hooks/e7g1es1k838c3pxkqmaxb8nsjy"

CMD ["poetry", "run", "python" ,"-c", "import main; main.lambda_handler({}, {})"]