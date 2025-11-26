# Render Environment Variables Setup Guide

## Google Sheets Credentials için Environment Variables

Render dashboard'da "Environment Variables" bölümüne şu değişkenleri ekleyin:

### Seçenek 1: Tek JSON değişken (Kolay)
```
Key: GCP_SERVICE_ACCOUNT
Value: (Tüm service account JSON'unuzu buraya yapıştırın)
```

### Seçenek 2: Ayrı değişkenler (Önerilen)
```
GCP_SERVICE_ACCOUNT_TYPE=service_account
GCP_SERVICE_ACCOUNT_PROJECT_ID=your-project-id
GCP_SERVICE_ACCOUNT_PRIVATE_KEY_ID=your-private-key-id
GCP_SERVICE_ACCOUNT_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nYOUR-KEY\n-----END PRIVATE KEY-----\n
GCP_SERVICE_ACCOUNT_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
GCP_SERVICE_ACCOUNT_CLIENT_ID=your-client-id
GCP_SERVICE_ACCOUNT_AUTH_URI=https://accounts.google.com/o/oauth2/auth
GCP_SERVICE_ACCOUNT_TOKEN_URI=https://oauth2.googleapis.com/token
GCP_SERVICE_ACCOUNT_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
GCP_SERVICE_ACCOUNT_CLIENT_X509_CERT_URL=your-cert-url
```

## Streamlit Secrets'a Erişim

Eğer environment variables kullanıyorsanız, streamlit_app_v2.py'de secrets yerine
environment variables'dan okuyun.
