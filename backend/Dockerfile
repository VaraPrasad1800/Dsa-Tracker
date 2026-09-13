FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# ---------------------------------------------------------------------------
# System packages
# ---------------------------------------------------------------------------
# Install compiler/runtime toolchains required by the online judge.
# All packages are listed EXPLICITLY so the intent is unambiguous and the
# apt resolver cannot silently omit any of them.
#
#   gcc, g++              — C and C++ judge submissions (explicit; build-essential
#                           also pulls them in but naming them makes intent clear)
#   build-essential       — standard headers and make
#   libc6-dev             — C standard library headers; required for -lm
#   default-jdk-headless  — javac + java for Java submissions.
#                           NOTE: use default-jdk-headless, NOT openjdk-17-jdk-headless.
#                           python:3.10-slim is Debian Bullseye; openjdk-17-jdk-headless
#                           is not in Bullseye main repos (only in bullseye-backports),
#                           causing "E: Unable to locate package" build failures.
#                           default-jdk-headless is a virtual package that always resolves
#                           to the distro default (OpenJDK 11 on Bullseye, 17 on Bookworm).
#   libpq-dev             — required by psycopg2-binary (PostgreSQL adapter)
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    libc6-dev \
    default-jdk-headless \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME so javac/java reliably resolve JVM shared libraries.
# update-java-alternatives / default-jdk sets a symlink at this path.
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . /app/

# ---------------------------------------------------------------------------
# Build-time smoke test
# Verifies every required compiler/runtime is reachable on PATH.
# If any tool is missing the image build FAILS HERE, surfacing the
# problem during CI/CD rather than at runtime when a user submits code.
# ---------------------------------------------------------------------------
RUN echo "=== Judge runtime smoke test ===" \
    && gcc   --version | grep -m1 gcc \
    && g++   --version | grep -m1 g++ \
    && java  -version 2>&1 | grep -m1 version \
    && javac -version \
    && python3 --version \
    && echo "=== All judge runtimes present ==="

EXPOSE 10000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers 2 --timeout 120"]
