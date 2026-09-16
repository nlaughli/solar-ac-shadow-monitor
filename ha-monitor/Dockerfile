FROM ghcr.io/home-assistant/aarch64-base:latest

ARG BUILD_ARCH
ARG BUILD_VERSION
LABEL \
  io.hass.type="addon" \
  io.hass.arch="${BUILD_ARCH}" \
  io.hass.version="${BUILD_VERSION}"

RUN apk add --no-cache python3 tzdata

WORKDIR /app
COPY solar_ac /app/solar_ac
COPY run.py /app/run.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]