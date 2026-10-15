# SharePoint Excel → Google Sheets otomatik eşitleme (Power Automate)

Bu rehber, SharePoint/OneDrive'da sürekli güncellenen bir Excel dosyasını belirli aralıklarla
dashboard'un okuduğu Google Sheets dosyasına kopyalayan bir Power Automate akışının nasıl
kurulacağını anlatır. Akış kurulduktan sonra dashboard'da hiçbir şey değiştirmek gerekmez.

```
Excel (SharePoint)  ──[Power Automate, 15 dk'da bir]──▶  Google Sheets  ──▶  Dashboard
```

**Süre:** 30–45 dakika · **Gerekenler:** Power Automate erişimi olan bir Microsoft 365 hesabı,
dashboard'un bağlı olduğu Google Sheets dosyasına düzenleme yetkisi olan bir Google hesabı.

---

## 0. Başlamadan önce

### Lisans kontrolü
Akış iki bağlayıcı kullanır: **Excel Online (Business)** (standart) ve **Google Sheets**.
Google Sheets bağlayıcısı bazı lisanslarda *Premium* olarak işaretlidir. Power Automate'te
**Bağlantılar → Yeni bağlantı → Google Sheets** ekranında "Premium" etiketi görürseniz lisansınızın
premium bağlayıcıları kapsadığını IT ekibiyle doğrulayın.

### Excel dosyasını hazırlayın
Power Automate yalnızca **Excel tablolarını** okuyabilir; düz hücre aralıklarını okuyamaz.

1. Excel dosyasını açın, veri aralığında herhangi bir hücreye tıklayın.
2. **Ekle → Tablo** (Ctrl+T) seçin, "Tablomda başlıklar var" kutusunu işaretleyin.
3. **Tablo Tasarımı** sekmesinde tabloya anlamlı bir ad verin, örn. `tblLeads` veya `tblDaily`.
4. Başlık satırında birleştirilmiş hücre, boş başlık veya aynı adlı iki kolon olmamalı.

Dosyaya yeni satırlar tablonun hemen altına eklendiği sürece tablo kendiliğinden büyür.

### Google Sheets'i hazırlayın
Dashboard şu sayfa adlarını ve kolonları bekler. Excel'deki veriyi hangi sayfaya yazacağınızı
seçin ve hedef sayfanın **1. satırına** başlıkları birebir yazın:

| Sayfa | Ne zaman | Başlıklar (1. satır) |
|---|---|---|
| `Daily` | Excel'de her satır bir gün (veya gün + kaynak) toplamı ise | `Date`, `Source`, `Total Leads`, `Qualified Leads`, `Viewings Scheduled`, `Viewings Completed`, `Offers Made`, `Offers Accepted`, `Closed Sales`, `Daily Budget` |
| `Leads` | Excel'de her satır tek bir lead ise | `Lead ID`, `Date`, `Source`, `Stage`, `Budget`, `Last Contact`, `Last Message` |
| `WhatsApp` | WhatsApp günlük sayıları | `Date`, `Messages Answered`, `Relevant`, `Irrelevant`, `Positive`, `Negative`, `Scheduled Leads` |

`Source`, `Daily Budget` gibi kolonlar isteğe bağlıdır; Excel'de karşılığı yoksa başlığı yazıp boş
bırakabilirsiniz.

> **GDPR:** `Leads` sayfasına isim, e-posta veya telefon yazmayın. `Lead ID` olarak CRM'deki
> takma kimliği kullanın. Excel'de kişisel veri varsa akışta o kolonları eşlemeyin; aşağıdaki
> 4. adımda yalnızca gereken kolonları seçiyorsunuz.

---

## 1. Akışı oluşturun

1. <https://make.powerautomate.com> adresine girin.
2. **Oluştur → Zamanlanmış bulut akışı** seçin.
3. Ad: `Excel → Sheets eşitleme (Dashboard)`
4. Tekrar: **15 dakikada bir** (veri dashboard'a en geç ~16 dakikada yansır). Daha az sık
   güncellenen veriler için 1 saat yeterlidir.
5. **Oluştur**'a tıklayın.

## 2. Excel'den satırları okuyun

1. **+ Yeni adım → Excel Online (Business) → Tabloda bulunan satırları listele**
   (*List rows present in a table*).
2. Alanlar:
   - **Konum:** dosyanın bulunduğu yer. Dosya başka birinin OneDrive'ındaysa
     *OneDrive for Business* değil, dosyayı sizinle paylaşan kişinin sitesini seçmeniz gerekebilir.
     Kolay yol: dosyayı ekibin ortak **SharePoint sitesine** taşıyıp oradan seçmek. Kişisel
     OneDrive'daki dosya, sahibi ayrılırsa veya paylaşımı kaldırırsa akışı bozar.
   - **Belge Kitaplığı:** `Belgeler` / `Documents`
   - **Dosya:** Excel dosyası
   - **Tablo:** 0. adımda verdiğiniz ad (`tblLeads` vb.)
3. **Gelişmiş parametreleri göster:**
   - **DateTime Format:** `ISO 8601` seçin. Seçmezseniz tarihler `45577` gibi sayılar olarak gelir
     ve dashboard tarihleri okuyamaz.
4. Adımın **⋯ → Ayarlar** menüsünde **Sayfalandırma**'yı açın ve **Eşik** değerini `5000` yapın.
   Varsayılan olarak yalnızca ilk 256 satır okunur.

## 3. Google Sheets'teki eski satırları temizleyin

Bu akış her çalışmada hedef sayfayı Excel'in birebir kopyasına dönüştürür (tam yenileme). Böylece
Excel'de silinen veya düzeltilen satırlar da Sheets'e yansır.

1. **+ Yeni adım → Google Sheets → Satırları al** (*Get rows*).
   - İlk kullanımda Google hesabınızla oturum açın.
   - **Dosya:** dashboard'un Google Sheets dosyası
   - **Çalışma sayfası:** hedef sayfa (`Leads`, `Daily` …)
2. **+ Yeni adım → Denetim → Her birine uygula** (*Apply to each*).
   - Girdi: önceki adımın **value** çıktısı.
   - İçine **Google Sheets → Satırı sil** (*Delete row*) ekleyin:
     - Dosya ve çalışma sayfası: aynı
     - **Satır kimliği:** dinamik içerikten `Row id` (`__PowerAppsId__`) seçin.

> Google Sheets bağlayıcısı satırları tanımak için sayfaya gizli bir `__PowerAppsId__` kolonu
> ekleyebilir. Dashboard bu kolonu yok sayar; silmeyin.

## 4. Excel satırlarını Sheets'e yazın

1. **+ Yeni adım → Denetim → Her birine uygula**.
   - Girdi: 2. adımdaki Excel adımının **value** çıktısı.
2. İçine **Google Sheets → Satır ekle** (*Insert row*) ekleyin:
   - Dosya ve çalışma sayfası: hedef sayfa.
   - Sayfadaki her başlık için bir alan çıkar. Her alana Excel'deki karşılık gelen kolonu
     dinamik içerikten seçin (eşleme tablosu: 6. bölüm).
3. Döngünün **⋯ → Ayarlar** menüsünde **Eşzamanlılık denetimi**'ni açın, paralellik derecesini
   `10` yapın. Yüzlerce satırda akışı birkaç kat hızlandırır.

## 5. Kaydedin ve test edin

1. **Kaydet** → **Test → El ile → Test et**.
2. Çalışma bitince Google Sheets'te satırların geldiğini, tarihlerin `2026-10-14` biçiminde
   olduğunu kontrol edin.
3. Dashboard'da **Refresh** butonuna basın. Başlıkta "Live · Google Sheets" ve doğru tarih
   aralığı görünmeli.

---

## 6. Kolon eşleme tablosu

Excel'deki kolon adları dashboard'unkilerden farklı olabilir. Aşağıyı Excel'in gerçek başlıklarıyla
doldurun ve 4. adımda buna göre eşleyin.

| Google Sheets başlığı | Excel'deki kolon | Not |
|---|---|---|
| `Lead ID` | | Kişisel veri değil, takma kimlik |
| `Date` | | Lead'in geldiği tarih |
| `Source` | | Google Ads, Meta Ads, Instagram, Organic … |
| `Stage` | | Aşağıdaki listeden biri olmalı |
| `Budget` | | Örn. `£2M–£3.5M` |
| `Last Contact` | | Son temas tarihi |
| `Last Message` | | Lead'in son mesajı (AI skorlama bunu okur) |

`Stage` değerleri tam olarak şunlardan biri olmalıdır: `New`, `Contacted`, `Qualified`,
`Viewing Scheduled`, `Viewing Completed`, `Offer Made`, `Offer Accepted`, `Closed`, `Lost`.
Excel'de farklı adlar kullanılıyorsa (örn. Türkçe aşamalar) **Satır ekle** adımında ilgili alana
bir ifade yazarak dönüştürebilirsiniz, örneğin:

```
if(equals(items('Apply_to_each_2')?['Aşama'], 'Görüşme Yapıldı'), 'Viewing Completed', items('Apply_to_each_2')?['Aşama'])
```

Çok sayıda eşleme varsa Excel'e bir yardımcı kolon (`=DÜŞEYARA(...)`) eklemek daha kolaydır.

---

## 7. Sorun giderme

| Belirti | Neden / çözüm |
|---|---|
| Sheets'e sadece 256 satır geliyor | 2. adımda sayfalandırma açık değil |
| Tarihler `45577` gibi sayı | 2. adımda DateTime Format `ISO 8601` seçilmemiş |
| "The resource could not be found" | Dosya taşındı/yeniden adlandırıldı veya tablo adı değişti; 2. adımda yeniden seçin |
| Akış birkaç hafta sonra duruyor | Bağlantının oturumu süresi dolmuş; **Bağlantılar** sayfasında Excel ve Google bağlantılarını yeniden doğrulayın |
| Dashboard'da birkaç saniye boş veri | Akış silme ile ekleme arasındayken sayfa okunmuş; bir sonraki yenilemede düzelir. Sık oluyorsa akış sıklığını azaltın |
| Akış çok uzun sürüyor (binlerce satır) | Eşzamanlılık değerini artırın; satır sayısı 5.000'i aşıyorsa Excel'i sadece son 90 günü içerecek şekilde filtreleyin |
| Hata bildirimi almak istiyorum | Akışın sonuna **Paralel dal → Çalıştırma koşulunu yapılandır: başarısız** + **Outlook → E-posta gönder** ekleyin |

---

## 8. Sonraki adım (isteğe bağlı)

Satır sayısı büyürse veya Sheets'i aradan çıkarmak isterseniz, dashboard Excel dosyasını Microsoft
Graph API ile doğrudan okuyabilir. Bunun için IT ekibinin Azure'da bir uygulama kaydı açıp dosyaya
okuma izni vermesi gerekir.
