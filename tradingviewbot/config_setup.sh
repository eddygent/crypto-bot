echo "Creating config.py file!"

echo "apiKey = 'your.email@website.com'" > config.py
echo "apiSecret = 'API_SECRET'" >> config.py
# I have multiple etrade accounts so this is helpful to segregate
echo "email = 'YOUR EMAIL'" >> config.py
echo "password = 'YOUR PASSWORD'" >> config.py
echo "exchange_id = 'YOUR EXCHANGE ID'" >> config.py
echo "Setup of config is complete!"
echo "Removing setup config file!"
rm -f setup_etrade_config.sh
