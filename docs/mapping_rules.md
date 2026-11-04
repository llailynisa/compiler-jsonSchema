# Aturan Pemetaan JSON Schema → Java

Dokumen ini adalah pegangan untuk `lowering.py` (membuat IR) dan `codegen.py`
(mencetak Java). Kalau hasil compiler tidak sesuai dokumen ini, berarti ada bug
di kode atau aturannya perlu direvisi di sini lebih dulu.

Pemilik: B. Status: draf awal. Bagian bertanda **[konfirmasi]** adalah keputusan
desain yang perlu disepakati A dan B.

---

## 1. Fitur yang didukung

| JSON Schema | Dukungan |
|---|---|
| `string`, `integer`, `number`, `boolean` | ✅ |
| `object` + `properties` | ✅ |
| `required` | ✅ |
| `array` + `items` | ✅ |
| `enum` (nilai string) | ✅ |
| object bertingkat inline di dalam `properties` atau `items` | ✅ |
| enum inline di dalam property atau `items` | ❌ ditolak (E104); definisikan di `$defs` lalu gunakan `$ref` |
| `$ref` lokal ke `$defs` | ✅ |
| array bertingkat | ✅ diturunkan rekursif menjadi `List<List<...>>` |
| `oneOf` / `anyOf` / `allOf`, `patternProperties`, `$ref` eksternal | ❌ tidak ditangani |
| enum dengan anggota non-string | diterima; nilai scalar dikonversi ke teks |

Validasi semantic tidak menolak keyword yang tidak dikenal seperti
`oneOf`/`patternProperties` jika keyword itu muncul bersama skema yang valid.
Keyword tersebut diabaikan oleh lowering. Enum hanya menjadi `EnumIR` bila
`type`-nya `string` dan `enum` berupa array. Anggota string, angka, boolean,
dan `null` dikonversi ke teks. Anggota berupa object atau array dikonversi
menjadi teks kosong, sehingga nama konstantanya menjadi `VALUE`; nama konstanta
duplikat kemudian ditolak oleh pemeriksaan IR.

---

## 2. Pemetaan tipe dasar

Tipe primitif atau wrapper ditentukan oleh `required`.

| JSON Schema | Required | Tidak required |
|---|---|---|
| `"type": "string"` | `String` | `String` |
| `"type": "integer"` | `int` | `Integer` |
| `"type": "number"` | `double` | `Double` |
| `"type": "boolean"` | `boolean` | `Boolean` |

Alasan: field wajib tidak boleh `null`, jadi cukup primitif. Field opsional bisa
kosong, jadi butuh wrapper yang boleh `null`. `String` selalu objek sehingga
sama di kedua kasus.

---

## 3. Pemetaan struktur

| JSON Schema | Hasil Java |
|---|---|
| `object` + `properties` | satu `class`, satu field per property |
| `array` + `items` bertipe T | `List<T>`, T diturunkan seolah tidak required (`List<Integer>`, bukan `List<int>`) |
| `array` + `items` berupa object inline atau `$ref` ke object | `List<NamaClass>`, dan class dibuat terpisah |
| `enum` | satu `enum` terpisah |
| object dari `$defs` yang dirujuk dengan `$ref` | class terpisah, dipakai sebagai tipe field |
| object inline di dalam `properties` atau `items` | class terpisah, dinamai dari property; untuk item array, dari nama property array |
| `$ref: "#/$defs/X"` | tipe hasil definisi `X`; object/enum memakai nama `X`, alias ditelusuri |

Array tidak punya primitif/wrapper: lowering meneruskan `required=False` ke tipe
item. Jika item-nya array, proses ini berulang; misalnya array dari integer
menjadi `List<Integer>` dan array dari array integer menjadi
`List<List<Integer>>`. Status required pada field array hanya mengatur metadata
field, bukan tipe `List`.

`$ref` ke `$defs` yang berisi object atau enum menggunakan nama tipe hasil
konversi dari nama definisi. `$ref` ke definisi alias scalar/array ditelusuri
hingga mendapatkan tipe akhirnya. Perlindungan terhadap alias yang melingkar
menghasilkan `Object`; siklus referensi object langsung tetap menggunakan nama
class object tersebut.

Lowering mengembalikan IR kosong jika AST bukan object. Untuk AST object, root
hanya dijadikan definisi bila memiliki `type`; `$defs` tetap diproses. Definisi
yang bukan object atau enum string tidak menghasilkan node IR sendiri. Dalam
alur CLI, semantic analysis dijalankan lebih dulu dan biasanya menolak skema
yang tidak valid sebelum lowering.

---

## 4. Aturan penamaan

### 4.1 Nama class dan enum (PascalCase)

| Sumber | Nama Java |
|---|---|
| root schema | dari `title` bila ada, kalau tidak `Schema` |
| property bertipe object inline | nama property → PascalCase. `profile` → `Profile` |
| item array berupa object inline | nama property array → PascalCase. `addresses` → `Addresses` |
| entri di `$defs` | nama kuncinya apa adanya → PascalCase. `Address` → `Address` |

Object inline didukung. Setiap object inline menghasilkan class tersendiri;
object di `items` memakai nama property array. Lowering menambahkan class inline
ke IR saat menemukannya, sehingga class inline bisa muncul sebelum class yang
memuat field tersebut.

### 4.2 Nama field (camelCase)

`first-name` → `firstName`, `user_id` → `userId`, `Age` → `age`.
Nama asli JSON disimpan di `FieldIR.json_name`.

### 4.3 Konstanta enum (UPPER_SNAKE_CASE)

| Nilai JSON | Konstanta Java |
|---|---|
| `active` | `ACTIVE` |
| `in-progress` | `IN_PROGRESS` |
| `in progress` | `IN_PROGRESS` |
| `2fa` | `_2FA` (diawali `_` karena identifier tidak boleh diawali angka) |

Nilai asli disimpan di `EnumIR.json_values`.

### 4.4 Cara konversi

1. Pecah nama pada karakter bukan huruf/angka (`-`, `_`, spasi, dan lainnya).
2. Gabungkan kata sesuai gaya: PascalCase, camelCase, atau UPPER_SNAKE_CASE.
   Kapitalisasi selain huruf pertama kata umumnya dipertahankan dari input.
3. Jika hasil diawali angka, tambahkan `_` di depan.
4. Nama kosong menjadi `Unnamed` (class), `field` (field), atau `VALUE`
   (konstanta enum).
5. Jika hasil konversi nama class, field, atau konstanta sama persis dengan
   reserved word Java yang tercantum di `lowering.py`, helper lowering
   menambahkan `_` di belakang.

### 4.5 Reserved word dan bentrok

Semantic analysis menolak nama property yang teks aslinya merupakan reserved
word Java, serta bentrok nama field atau tipe setelah konversi, dengan E204.
Jadi property bernama `class` ditolak, walaupun helper lowering sendiri akan
mengubahnya menjadi `class_`. Nama tipe (root, `$defs`, dan object inline)
yang merupakan reserved word setelah konversi tidak ditolak semata-mata karena
reserved word; helper lowering menambahkan `_`. Bentrok nama tipe tetap
dilaporkan sebagai E204.

Lowering juga dapat menghasilkan nama konstanta enum yang sama dari nilai
berbeda. Kondisi itu tidak dilaporkan oleh semantic analysis; pemeriksaan IR
(`check_ir`) mendeteksinya sebagai konstanta enum ganda dan CLI menghentikan
code generation.

---

## 5. Pemetaan error semantic (usulan kode)

Kode final ditetapkan di `error_codes.md`. Di sini hanya hubungan aturan dan
kodenya.

| Kode | Kondisi | Contoh |
|---|---|---|
| E101 | `$ref` menunjuk ke definisi yang tidak ada atau bukan `$ref` lokal | `"$ref": "#/$defs/Foo"` tetapi `Foo` tidak ada |
| E102 | nama di `required` tidak ada di `properties` | `"required": ["email"]` tanpa property `email` |
| E103 | nilai `type` tidak dikenal atau tidak tersedia | `"type": "text"` |
| E104 | enum inline tidak didukung | enum harus diletakkan di `$defs` dan dirujuk dengan `$ref` |
| E204 | nama field atau tipe hasil konversi bentrok; property teks aslinya memakai reserved word Java | `first-name` dan `first_name`, atau property `class` |

---

## 6. Contoh lengkap

### Input (JSON Schema)

```json
{
  "title": "User",
  "type": "object",
  "properties": {
    "name":    { "type": "string" },
    "age":     { "type": "integer" },
    "status":  { "$ref": "#/$defs/Status" },
    "tags":    { "type": "array", "items": { "type": "string" } },
    "address": { "$ref": "#/$defs/Address" },
    "profile": {
      "type": "object",
      "properties": { "bio": { "type": "string" } }
    }
  },
  "required": ["name", "age"],
  "$defs": {
    "Status": { "type": "string", "enum": ["active", "in-progress"] },
    "Address": {
      "type": "object",
      "properties": { "city": { "type": "string" } },
      "required": ["city"]
    }
  }
}
```

### Hasil lowering (IR, format `dump_ir`)

```
ClassIR Profile
  - bio: String
ClassIR User
  - name: String [required]
  - age: int [required]
  - status: Status
  - tags: List<String>
  - address: Address
  - profile: Profile
EnumIR Status
  - ACTIVE   (json: "active")
  - IN_PROGRESS   (json: "in-progress")
ClassIR Address
  - city: String [required]
```

Perhatikan `age` menjadi `int` karena required, sedangkan `status` bukan
required sehingga tidak ada pengaruh primitif/wrapper (tipenya enum). Enum
menjadi `EnumIR` bila didefinisikan sebagai `type: "string"` dengan `enum`
berupa array.

### Output (Java)

Empat file: `User.java`, `Address.java`, `Profile.java`, dan `Status.java`.
Dua di antaranya ditampilkan di bawah.

`Status.java`

```java
public enum Status {
    ACTIVE,
    IN_PROGRESS
}
```

`User.java`

```java
import java.util.List;

public class User {
    private String name;
    private int age;
    private Status status;
    private List<String> tags;
    private Address address;
    private Profile profile;

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public int getAge() { return age; }
    public void setAge(int age) { this.age = age; }

    // getter/setter untuk status, tags, address, profile mengikuti pola yang sama
}
```

Catatan: `import java.util.List;` hanya muncul karena `User` punya field
`List<...>` (dicek lewat `ClassIR.uses_list()`).

---

## 7. Keputusan yang perlu dikonfirmasi

1. Nama class root: `title` dengan cadangan `Schema`.
2. Nama class object inline dalam property atau item array: nama property dalam PascalCase.
3. Output class hanya `private` field + getter + setter (tanpa constructor,
   `toString`, dan sebagainya).
4. Semua file di default package (tanpa baris `package`).
5. Kode error semantik mengikuti `compiler/semantic.py`; E201 sampai E203 tidak digunakan.
