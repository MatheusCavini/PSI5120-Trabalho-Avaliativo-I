# Imagem mínima para empacotar a aplicação Python do Trabalho Avaliativo 1.
# A aplicação usa apenas a biblioteca padrão do Python, então não há
# dependências para instalar via pip — isso mantém a imagem pequena e
# simplifica o build tanto localmente quanto no CloudShell.
FROM python:3.12-slim

# Cria um usuário não-root dedicado para executar a aplicação
# (boa prática de segurança: evita rodar o processo como root no container).
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Copia apenas o arquivo necessário.
COPY app.py .

# Cria o diretório de dados (contador persistido) e ajusta a posse
# para o usuário não-root antes de trocar de usuário.
RUN mkdir -p /data && chown -R appuser:appuser /data /app

USER appuser

ENV APP_PORT=8080
EXPOSE 8080

CMD ["python3", "app.py"]
