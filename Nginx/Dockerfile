FROM nginx
EXPOSE 80
EXPOSE 443
COPY default.conf /etc/nginx/conf.d/
COPY htpasswd /etc/nginx/.htpasswd
COPY vestec.crt /etc/nginx/
COPY vestec.key /etc/nginx/
COPY index.html /var/www/index.html
CMD ["nginx", "-g", "daemon off;"]
