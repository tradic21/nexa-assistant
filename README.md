
# Nexa – Multimodalni desktop asistent

Nexa je desktop aplikacija razvijena u sklopu diplomskog rada na Fakultetu organizacije i informatike u Varaždinu. Omogućuje upravljanje računalom pomoću **gesta ruku i glasovnih naredbi**, uz mogućnost komunikacije s AI asistentom.

## Glavne funkcionalnosti

- **Upravljanje gestama:** pomicanje kursora, klikovi, povlačenje elemenata, pomicanje sadržaja te podešavanje glasnoće i svjetline.
- **Glasovno upravljanje:** otvaranje aplikacija, upravljanje prozorima, pretraživanje i izvršavanje naredbi.
- **AI asistent:** postavljanje pitanja glasom ili tekstom i primanje odgovora.
- **Grafičko sučelje:** prikaz prepoznatih naredbi, statusa slušanja i razgovora s asistentom.

## Korištene tehnologije

- **Programski jezik:** Python
- **Prepoznavanje gesta:** MediaPipe, OpenCV
- **Prepoznavanje govora:** Vosk, Google Speech Recognition
- **Grafičko sučelje:** PySide6
- **Umjetna inteligencija:** OpenAI API

## Instalacija i pokretanje

1. Klonirati repozitorij:
   ```bash
   git clone https://github.com/tradic21/nexa-assistant.git
   cd nexa-assistant
   ```

2. Instalirati potrebne biblioteke:
   ```bash
   pip install -r requirements.txt
   ```

3. Preuzeti model `vosk-model-small-en-us-0.15` i smjestiti ga u glavnu mapu projekta.

4. Postaviti vlastiti OpenAI API ključ u varijablu okruženja `OPENAI_API_KEY`.

5. Pokrenuti aplikaciju:
   ```bash
   python main.py
   ```

**Napomena:** Aplikacija je razvijena i testirana na operacijskom sustavu Windows. Za korištenje glasovnih naredbi i prepoznavanja gesta potrebni su mikrofon i kamera.
