"""The words of the About page (with its Privacy section), in every site language.

English and Bosnian are written with care; the other languages are short AI translations of
them, as the page itself says. The page's own links ("About", "Privacy") live with the rest of
the interface text in site/ui.js (`aboutNav`), because the app page shows them too.

What the privacy section claims is checked by tests/test_about.py against the site's own
scripts: the third parties named here are the only hosts a page may contact.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AboutText:
    description: str                    # the meta description and the lead under the title
    made_title: str
    made: str
    honest_title: str
    honest: str
    disclaimer_title: str
    disclaimer: str
    sources_title: str
    sources: str                        # introduces the list of sources
    notices: str                        # the link to THIRD_PARTY_NOTICES.md
    free_title: str
    free: str
    privacy_title: str
    privacy_points: tuple[str, ...]
    third_parties: str                  # exactly which third parties a page may contact
    github_privacy: str                 # the link to GitHub's privacy statement


ABOUT: dict[str, AboutText] = {
    "en": AboutText(
        description="Fiʿl is a free study aid for the Arabic of the Quran: verbs, nouns, adjectives and particles, with forms, ayat, audio and practice.",
        made_title="Who made it",
        made="Fiʿl was made by a programmer together with Claude Code, Anthropic's AI coding tool. It is an attempt to use modern technology, AI and AI tools, to make learning the Arabic of the Quran easier.",
        honest_title="How it is made",
        honest="The explanations, the translations into the site's languages, the practice sentences and the reviews are produced with AI. They are checked by automatic tests: grammar, every form against the Quranic Arabic Corpus, licence checks and audio checks. English and Bosnian are the main languages; the other languages are AI translations.",
        disclaimer_title="Please note",
        disclaimer="This site is a learning aid. It is not a religious authority, not tafsir and not a fatwa, and it may contain mistakes. The Arabic text of the Quran itself comes from Tanzil (a verified text); everything around it is a study aid only. For any religious question, consult qualified scholars and trusted translations.",
        sources_title="Sources and licences",
        sources="Fiʿl is built on the work of others, credited in the footer of every page:",
        notices="All sources, their licences and how we keep to them: THIRD_PARTY_NOTICES.md on GitHub",
        free_title="Free for good",
        free="No ads, no payments, no registration.",
        privacy_title="Privacy",
        privacy_points=(
            "No cookies, no tracking, no analytics and no account.",
            "Your progress and settings (the language you chose, the verbs you know) are kept only in your own browser (localStorage). They are never sent anywhere; clearing the site data in your browser deletes them.",
            "The pages, the audio and the data are static files served by GitHub Pages. GitHub may log requests, as any web host does.",
            "To work offline, the site keeps copies of the pages you open in your browser's cache, on your own device.",
        ),
        third_parties="A page may contact these third parties and no others: Google Fonts (fonts.googleapis.com and fonts.gstatic.com) loads the typefaces when a page opens, and the recitation of a whole ayah is streamed from the Islamic Network CDN (cdn.islamic.network, behind alquran.cloud) only when you press play on it. Links to quran.com, quranwbw.com and islam.ba are ordinary links: they are contacted only if you click.",
        github_privacy="GitHub's privacy statement",
    ),
    "bs": AboutText(
        description="Fiʿl je besplatna pomoć za učenje arapskog jezika Kur'ana: glagoli, imenice, pridjevi i čestice, s oblicima, ajetima, zvukom i vježbama.",
        made_title="Ko ga je napravio",
        made="Fiʿl je napravio programer zajedno s Claude Codeom, Anthropicovim AI alatom za programiranje. To je pokušaj da se savremena tehnologija, vještačka inteligencija i AI alati, upotrijebi kako bi učenje arapskog jezika Kur'ana bilo lakše.",
        honest_title="Kako je napravljen",
        honest="Objašnjenja, prijevodi na jezike stranice, rečenice za vježbu i pregledi nastaju uz pomoć vještačke inteligencije. Provjeravaju ih automatski testovi: gramatika, svaki oblik prema Quranic Arabic Corpusu, provjere licenci i provjere zvuka. Engleski i bosanski su glavni jezici; ostali jezici su AI prijevodi.",
        disclaimer_title="Napomena",
        disclaimer="Ova stranica je pomoć za učenje. Nije vjerski autoritet, nije tefsir niti fetva i može sadržavati greške. Sam arapski tekst Kur'ana potječe s Tanzila (provjeren tekst); sve oko njega je samo pomagalo za učenje. Za svako vjersko pitanje obratite se stručnim učenjacima i provjerenim prijevodima.",
        sources_title="Izvori i licence",
        sources="Fiʿl počiva na tuđem radu, koji je naveden u podnožju svake stranice:",
        notices="Svi izvori, njihove licence i način na koji ih poštujemo: THIRD_PARTY_NOTICES.md na GitHubu",
        free_title="Besplatno zauvijek",
        free="Bez reklama, bez plaćanja, bez registracije.",
        privacy_title="Privatnost",
        privacy_points=(
            "Nema kolačića, praćenja, analitike ni korisničkog računa.",
            "Tvoj napredak i postavke (odabrani jezik, glagoli koje znaš) čuvaju se samo u tvom pregledniku (localStorage). Nikamo se ne šalju; brisanjem podataka stranice u pregledniku nestaju.",
            "Stranice, zvuk i podaci su statične datoteke koje poslužuje GitHub Pages. GitHub može bilježiti zahtjeve, kao i svaki web-poslužitelj.",
            "Da bi radila bez interneta, stranica čuva kopije stranica koje otvoriš u kešu tvog preglednika, na tvom uređaju.",
        ),
        third_parties="Stranica može kontaktirati ove treće strane i nijednu drugu: Google Fonts (fonts.googleapis.com i fonts.gstatic.com) učitava pisma kad se stranica otvori, a recitacija cijelog ajeta prenosi se s Islamic Network CDN-a (cdn.islamic.network, iza alquran.cloud) tek kad pritisneš play. Veze na quran.com, quranwbw.com i islam.ba su obične veze: kontaktiraju se samo ako klikneš.",
        github_privacy="GitHubova izjava o privatnosti",
    ),
    "tr": AboutText(
        description="Fiʿl, Kur'an Arapçasını öğrenmek için ücretsiz bir yardımcıdır: fiiller, isimler, sıfatlar ve edatlar; biçimler, ayetler, ses ve alıştırmalarla.",
        made_title="Kim yaptı",
        made="Fiʿl, bir programcı tarafından Anthropic'in yapay zekâ kodlama aracı Claude Code ile birlikte yapıldı. Kur'an Arapçasını öğrenmeyi kolaylaştırmak için modern teknolojiyi, yapay zekâyı ve yapay zekâ araçlarını kullanma denemesidir.",
        honest_title="Nasıl yapıldı",
        honest="Açıklamalar, sitenin dillerine çeviriler, alıştırma cümleleri ve incelemeler yapay zekâ ile üretilir. Otomatik testlerle denetlenir: dil bilgisi, her biçim Quranic Arabic Corpus'a karşı, lisans ve ses denetimleri. İngilizce ve Boşnakça ana dillerdir; diğer diller yapay zekâ çevirileridir.",
        disclaimer_title="Lütfen dikkat",
        disclaimer="Bu site bir öğrenme yardımcısıdır. Dinî bir otorite, tefsir ya da fetva değildir ve hatalar içerebilir. Kur'an'ın Arapça metni Tanzil'den gelir (doğrulanmış metin); çevresindeki her şey yalnızca öğrenme yardımıdır. Dinî her soru için yetkin âlimlere ve güvenilir mealere başvurun.",
        sources_title="Kaynaklar ve lisanslar",
        sources="Fiʿl başkalarının emeği üzerine kuruludur; her sayfanın altında belirtilir:",
        notices="Tüm kaynaklar, lisansları ve uyumumuz: GitHub'da THIRD_PARTY_NOTICES.md",
        free_title="Hep ücretsiz",
        free="Reklam yok, ödeme yok, kayıt yok.",
        privacy_title="Gizlilik",
        privacy_points=(
            "Çerez, izleme, analiz ve hesap yoktur.",
            "İlerlemeniz ve ayarlarınız (seçtiğiniz dil, bildiğiniz fiiller) yalnızca kendi tarayıcınızda (localStorage) tutulur. Hiçbir yere gönderilmez; tarayıcıdan site verilerini silmek onları siler.",
            "Sayfalar, ses ve veriler GitHub Pages'in sunduğu statik dosyalardır. GitHub, her web sunucusu gibi istekleri kaydedebilir.",
            "Çevrimdışı çalışmak için site, açtığınız sayfaların kopyalarını kendi cihazınızdaki tarayıcı önbelleğinde tutar.",
        ),
        third_parties="Bir sayfa yalnızca şu üçüncü taraflara bağlanabilir: Google Fonts (fonts.googleapis.com ve fonts.gstatic.com) sayfa açılırken yazı tiplerini yükler; bir ayetin tamamının tilaveti, yalnızca siz oynat'a bastığınızda Islamic Network CDN'inden (cdn.islamic.network, alquran.cloud arkasında) akıtılır. quran.com, quranwbw.com ve islam.ba bağlantıları sıradan bağlantılardır: yalnızca tıklarsanız bağlanılır.",
        github_privacy="GitHub gizlilik bildirimi",
    ),
    "fr": AboutText(
        description="Fiʿl est une aide gratuite pour apprendre l'arabe du Coran : verbes, noms, adjectifs et particules, avec formes, versets, audio et exercices.",
        made_title="Qui l'a fait",
        made="Fiʿl a été réalisé par un programmeur avec Claude Code, l'outil de programmation IA d'Anthropic. C'est une tentative d'utiliser la technologie moderne, l'IA et ses outils, pour faciliter l'apprentissage de l'arabe du Coran.",
        honest_title="Comment il est fait",
        honest="Les explications, les traductions dans les langues du site, les phrases d'exercice et les relectures sont produites avec l'IA. Elles sont vérifiées par des tests automatiques : grammaire, chaque forme comparée au Quranic Arabic Corpus, licences et audio. L'anglais et le bosnien sont les langues principales ; les autres sont des traductions IA.",
        disclaimer_title="À noter",
        disclaimer="Ce site est une aide à l'étude. Il n'est ni une autorité religieuse, ni un tafsir, ni une fatwa, et il peut contenir des erreurs. Le texte arabe du Coran vient de Tanzil (texte vérifié) ; tout le reste n'est qu'une aide à l'étude. Pour toute question religieuse, consultez des savants qualifiés et des traductions fiables.",
        sources_title="Sources et licences",
        sources="Fiʿl repose sur le travail d'autres personnes, cité au bas de chaque page :",
        notices="Toutes les sources, leurs licences et notre respect de celles-ci : THIRD_PARTY_NOTICES.md sur GitHub",
        free_title="Gratuit pour toujours",
        free="Pas de publicité, pas de paiement, pas d'inscription.",
        privacy_title="Confidentialité",
        privacy_points=(
            "Ni cookies, ni suivi, ni analyse, ni compte.",
            "Votre progression et vos réglages (la langue choisie, les verbes connus) restent uniquement dans votre navigateur (localStorage). Ils ne sont envoyés nulle part ; effacer les données du site les supprime.",
            "Les pages, l'audio et les données sont des fichiers statiques servis par GitHub Pages. GitHub peut journaliser les requêtes, comme tout hébergeur.",
            "Pour fonctionner hors ligne, le site garde des copies des pages ouvertes dans le cache de votre navigateur, sur votre appareil.",
        ),
        third_parties="Une page peut contacter ces tiers et aucun autre : Google Fonts (fonts.googleapis.com et fonts.gstatic.com) charge les polices à l'ouverture, et la récitation d'un verset entier est diffusée depuis le CDN d'Islamic Network (cdn.islamic.network, derrière alquran.cloud) seulement quand vous appuyez sur lecture. Les liens vers quran.com, quranwbw.com et islam.ba sont de simples liens : ils ne sont contactés que si vous cliquez.",
        github_privacy="Déclaration de confidentialité de GitHub",
    ),
    "id": AboutText(
        description="Fiʿl adalah alat bantu belajar gratis untuk bahasa Arab Al-Qur'an: kata kerja, kata benda, kata sifat dan partikel, dengan bentuk, ayat, audio dan latihan.",
        made_title="Siapa pembuatnya",
        made="Fiʿl dibuat oleh seorang programmer bersama Claude Code, alat pemrograman AI dari Anthropic. Ini upaya memakai teknologi modern, AI dan alat AI, agar belajar bahasa Arab Al-Qur'an lebih mudah.",
        honest_title="Cara pembuatannya",
        honest="Penjelasan, terjemahan ke bahasa situs, kalimat latihan dan tinjauan dibuat dengan AI. Semuanya diperiksa tes otomatis: tata bahasa, setiap bentuk terhadap Quranic Arabic Corpus, pemeriksaan lisensi dan audio. Bahasa Inggris dan Bosnia adalah bahasa utama; bahasa lain adalah terjemahan AI.",
        disclaimer_title="Catatan",
        disclaimer="Situs ini alat bantu belajar. Ia bukan otoritas agama, bukan tafsir dan bukan fatwa, dan mungkin mengandung kesalahan. Teks Arab Al-Qur'an berasal dari Tanzil (teks terverifikasi); semua yang lain hanyalah alat bantu belajar. Untuk pertanyaan agama, tanyakan kepada ulama yang berkompeten dan gunakan terjemahan tepercaya.",
        sources_title="Sumber dan lisensi",
        sources="Fiʿl dibangun di atas karya orang lain, yang dicantumkan di bagian bawah setiap halaman:",
        notices="Semua sumber, lisensinya dan cara kami mematuhinya: THIRD_PARTY_NOTICES.md di GitHub",
        free_title="Gratis selamanya",
        free="Tanpa iklan, tanpa pembayaran, tanpa pendaftaran.",
        privacy_title="Privasi",
        privacy_points=(
            "Tanpa cookie, pelacakan, analitik, atau akun.",
            "Kemajuan dan pengaturan Anda (bahasa pilihan, kata kerja yang dikuasai) hanya disimpan di peramban Anda (localStorage). Tidak pernah dikirim ke mana pun; menghapus data situs di peramban menghapusnya.",
            "Halaman, audio, dan data adalah berkas statis yang disajikan GitHub Pages. GitHub dapat mencatat permintaan, seperti penyedia web mana pun.",
            "Agar berjalan offline, situs menyimpan salinan halaman yang Anda buka di cache peramban pada perangkat Anda.",
        ),
        third_parties="Sebuah halaman hanya dapat menghubungi pihak ketiga ini: Google Fonts (fonts.googleapis.com dan fonts.gstatic.com) memuat huruf saat halaman dibuka, dan bacaan satu ayat penuh dialirkan dari CDN Islamic Network (cdn.islamic.network, di balik alquran.cloud) hanya saat Anda menekan putar. Tautan ke quran.com, quranwbw.com, dan islam.ba adalah tautan biasa: hanya dihubungi jika Anda mengkliknya.",
        github_privacy="Pernyataan privasi GitHub",
    ),
    "ur": AboutText(
        description="فعل قرآن کی عربی سیکھنے کا ایک مفت معاون ہے: افعال، اسماء، صفات اور حروف، صیغوں، آیات، آواز اور مشقوں کے ساتھ۔",
        made_title="کس نے بنایا",
        made="فعل ایک پروگرامر نے Anthropic کے AI کوڈنگ ٹول Claude Code کے ساتھ مل کر بنایا۔ یہ جدید ٹیکنالوجی، AI اور AI ٹولز سے قرآن کی عربی سیکھنا آسان بنانے کی ایک کوشش ہے۔",
        honest_title="یہ کیسے بنا",
        honest="وضاحتیں، سائٹ کی زبانوں میں تراجم، مشقی جملے اور جائزے AI سے تیار ہوتے ہیں۔ انہیں خودکار ٹیسٹ جانچتے ہیں: گرامر، ہر صیغہ Quranic Arabic Corpus سے، لائسنس اور آواز کی جانچ۔ انگریزی اور بوسنیائی بنیادی زبانیں ہیں؛ باقی زبانیں AI تراجم ہیں۔",
        disclaimer_title="براہِ کرم نوٹ کریں",
        disclaimer="یہ سائٹ سیکھنے کا ایک معاون ہے۔ یہ دینی اتھارٹی، تفسیر یا فتویٰ نہیں ہے اور اس میں غلطیاں ہو سکتی ہیں۔ قرآن کا عربی متن Tanzil سے ہے (تصدیق شدہ متن)؛ باقی سب کچھ صرف سیکھنے کی مدد ہے۔ ہر دینی سوال کے لیے مستند علماء اور معتبر تراجم سے رجوع کریں۔",
        sources_title="ماخذ اور لائسنس",
        sources="فعل دوسروں کے کام پر قائم ہے، جو ہر صفحے کے نیچے درج ہے:",
        notices="تمام ماخذ، ان کے لائسنس اور ہماری پابندی: GitHub پر THIRD_PARTY_NOTICES.md",
        free_title="ہمیشہ مفت",
        free="کوئی اشتہار نہیں، کوئی ادائیگی نہیں، کوئی رجسٹریشن نہیں۔",
        privacy_title="رازداری",
        privacy_points=(
            "کوئی کوکی، ٹریکنگ، اینالیٹکس یا اکاؤنٹ نہیں۔",
            "آپ کی پیش رفت اور ترتیبات (منتخب زبان، جو افعال آپ جانتے ہیں) صرف آپ کے اپنے براؤزر (localStorage) میں رہتی ہیں۔ یہ کہیں نہیں بھیجی جاتیں؛ براؤزر میں سائٹ کا ڈیٹا صاف کرنے سے مٹ جاتی ہیں۔",
            "صفحات، آواز اور ڈیٹا GitHub Pages کی فراہم کردہ جامد فائلیں ہیں۔ GitHub، ہر ویب ہوسٹ کی طرح، درخواستیں لاگ کر سکتا ہے۔",
            "آف لائن کام کے لیے سائٹ آپ کے کھولے ہوئے صفحات کی نقول آپ کے اپنے آلے پر براؤزر کیش میں رکھتی ہے۔",
        ),
        third_parties="کوئی صفحہ صرف ان تیسرے فریقوں سے رابطہ کر سکتا ہے: Google Fonts (fonts.googleapis.com اور fonts.gstatic.com) صفحہ کھلتے ہی فونٹ لوڈ کرتا ہے، اور پوری آیت کی تلاوت Islamic Network CDN (cdn.islamic.network، alquran.cloud کے پیچھے) سے صرف اس وقت چلتی ہے جب آپ پلے دبائیں۔ quran.com، quranwbw.com اور islam.ba کے لنک عام لنک ہیں: صرف کلک کرنے پر رابطہ ہوتا ہے۔",
        github_privacy="GitHub کا پرائیویسی بیان",
    ),
    "bn": AboutText(
        description="ফিʿল কুরআনের আরবি শেখার একটি বিনামূল্যের সহায়ক: ক্রিয়া, বিশেষ্য, বিশেষণ ও অব্যয়, রূপ, আয়াত, অডিও ও অনুশীলনসহ।",
        made_title="কে বানিয়েছে",
        made="ফিʿল একজন প্রোগ্রামার Anthropic-এর এআই কোডিং টুল Claude Code-এর সাথে মিলে বানিয়েছেন। কুরআনের আরবি শেখা সহজ করতে আধুনিক প্রযুক্তি, এআই ও এআই টুল ব্যবহারের একটি প্রচেষ্টা এটি।",
        honest_title="কীভাবে বানানো",
        honest="ব্যাখ্যা, সাইটের ভাষাগুলোতে অনুবাদ, অনুশীলনের বাক্য ও পর্যালোচনা এআই দিয়ে তৈরি। স্বয়ংক্রিয় পরীক্ষা এগুলো যাচাই করে: ব্যাকরণ, প্রতিটি রূপ Quranic Arabic Corpus-এর সাথে, লাইসেন্স ও অডিও পরীক্ষা। ইংরেজি ও বসনীয় প্রধান ভাষা; অন্য ভাষাগুলো এআই অনুবাদ।",
        disclaimer_title="অনুগ্রহ করে লক্ষ করুন",
        disclaimer="এই সাইট একটি শেখার সহায়ক। এটি ধর্মীয় কর্তৃপক্ষ, তাফসির বা ফতোয়া নয় এবং এতে ভুল থাকতে পারে। কুরআনের আরবি পাঠ Tanzil থেকে (যাচাইকৃত পাঠ); এর বাইরে সবকিছু শুধু শেখার সহায়তা। যেকোনো ধর্মীয় প্রশ্নে যোগ্য আলেম ও নির্ভরযোগ্য অনুবাদের শরণাপন্ন হোন।",
        sources_title="উৎস ও লাইসেন্স",
        sources="ফিʿল অন্যদের কাজের ওপর গড়া, যা প্রতিটি পাতার নিচে উল্লেখ আছে:",
        notices="সব উৎস, তাদের লাইসেন্স ও আমাদের মানার উপায়: GitHub-এ THIRD_PARTY_NOTICES.md",
        free_title="চিরকাল বিনামূল্যে",
        free="কোনো বিজ্ঞাপন নেই, কোনো পেমেন্ট নেই, কোনো নিবন্ধন নেই।",
        privacy_title="গোপনীয়তা",
        privacy_points=(
            "কোনো কুকি, ট্র্যাকিং, অ্যানালিটিক্স বা অ্যাকাউন্ট নেই।",
            "আপনার অগ্রগতি ও সেটিংস (বেছে নেওয়া ভাষা, জানা ক্রিয়া) শুধু আপনার নিজের ব্রাউজারে (localStorage) থাকে। কোথাও পাঠানো হয় না; ব্রাউজারে সাইটের ডেটা মুছলে সেগুলো মুছে যায়।",
            "পাতা, অডিও ও ডেটা GitHub Pages-এর দেওয়া স্ট্যাটিক ফাইল। যেকোনো ওয়েব হোস্টের মতো GitHub অনুরোধ লগ করতে পারে।",
            "অফলাইনে চলার জন্য সাইট আপনার খোলা পাতার কপি আপনার নিজের ডিভাইসে ব্রাউজারের ক্যাশে রাখে।",
        ),
        third_parties="একটি পাতা শুধু এই তৃতীয় পক্ষগুলোর সাথে যোগাযোগ করতে পারে: Google Fonts (fonts.googleapis.com ও fonts.gstatic.com) পাতা খোলার সময় ফন্ট লোড করে, আর পুরো আয়াতের তিলাওয়াত Islamic Network CDN (cdn.islamic.network, alquran.cloud-এর পেছনে) থেকে কেবল আপনি প্লে চাপলেই চলে। quran.com, quranwbw.com ও islam.ba-র লিংক সাধারণ লিংক: ক্লিক করলেই তাদের সাথে যোগাযোগ হয়।",
        github_privacy="GitHub-এর গোপনীয়তা বিবৃতি",
    ),
    "fa": AboutText(
        description="فِعل یک یار رایگان برای آموختن عربی قرآن است: فعل‌ها، اسم‌ها، صفت‌ها و حرف‌ها، با صیغه‌ها، آیه‌ها، صدا و تمرین.",
        made_title="چه کسی ساخته است",
        made="فِعل را یک برنامه‌نویس همراه با Claude Code، ابزار برنامه‌نویسی هوش مصنوعی شرکت Anthropic ساخته است. این تلاشی است برای به‌کار گرفتن فناوری نوین، هوش مصنوعی و ابزارهای آن، تا آموختن عربی قرآن آسان‌تر شود.",
        honest_title="چگونه ساخته شده",
        honest="توضیح‌ها، ترجمه‌ها به زبان‌های سایت، جمله‌های تمرین و بازبینی‌ها با هوش مصنوعی تولید می‌شوند. آزمون‌های خودکار آن‌ها را می‌سنجند: دستور زبان، هر صیغه در برابر Quranic Arabic Corpus، بررسی پروانه‌ها و صدا. انگلیسی و بوسنیایی زبان‌های اصلی‌اند؛ زبان‌های دیگر ترجمهٔ هوش مصنوعی‌اند.",
        disclaimer_title="توجه",
        disclaimer="این سایت ابزاری برای آموزش است. مرجع دینی، تفسیر یا فتوا نیست و ممکن است اشتباه داشته باشد. متن عربی خود قرآن از Tanzil است (متن راستی‌آزمایی‌شده)؛ هر چیز دیگر تنها کمک آموزشی است. برای هر پرسش دینی به عالمان شایسته و ترجمه‌های معتبر مراجعه کنید.",
        sources_title="منبع‌ها و پروانه‌ها",
        sources="فِعل بر کار دیگران استوار است که در پایین هر صفحه آمده است:",
        notices="همهٔ منبع‌ها، پروانه‌هایشان و پایبندی ما: THIRD_PARTY_NOTICES.md در GitHub",
        free_title="همیشه رایگان",
        free="بدون تبلیغ، بدون پرداخت، بدون ثبت‌نام.",
        privacy_title="حریم خصوصی",
        privacy_points=(
            "بدون کوکی، ردیابی، تحلیل یا حساب کاربری.",
            "پیشرفت و تنظیمات شما (زبان برگزیده، فعل‌هایی که می‌دانید) فقط در مرورگر خودتان (localStorage) می‌ماند. به هیچ جا فرستاده نمی‌شود؛ پاک کردن داده‌های سایت در مرورگر آن‌ها را از میان می‌برد.",
            "صفحه‌ها، صدا و داده‌ها فایل‌های ایستایی‌اند که GitHub Pages ارائه می‌کند. GitHub مانند هر میزبان وب ممکن است درخواست‌ها را ثبت کند.",
            "برای کار بدون اینترنت، سایت نسخه‌ای از صفحه‌هایی که باز می‌کنید را در حافظهٔ نهان مرورگر روی دستگاه خودتان نگه می‌دارد.",
        ),
        third_parties="یک صفحه تنها می‌تواند با این طرف‌های ثالث تماس بگیرد: Google Fonts (fonts.googleapis.com و fonts.gstatic.com) هنگام باز شدن صفحه قلم‌ها را بارگیری می‌کند، و قرائت یک آیهٔ کامل تنها وقتی پخش را می‌زنید از Islamic Network CDN (cdn.islamic.network، پشت alquran.cloud) پخش می‌شود. پیوند به quran.com، quranwbw.com و islam.ba پیوند ساده است: فقط اگر کلیک کنید با آن‌ها تماس گرفته می‌شود.",
        github_privacy="بیانیهٔ حریم خصوصی GitHub",
    ),
}
