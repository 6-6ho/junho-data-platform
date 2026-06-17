FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html

# noindex 헤더
RUN printf 'server {\n  listen 80 default_server;\n  add_header X-Robots-Tag "noindex, nofollow" always;\n  location / { root /usr/share/nginx/html; index index.html; }\n}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO /dev/null http://localhost/ || exit 1
