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
| nested object | ✅ |
| `$ref` lokal ke `$defs` | ✅ |
| `oneOf` / `anyOf` / `allOf`, `patternProperties`, `$ref` eksternal | ❌ di luar cakupan |
| array di dalam array, enum non-string | ❌ di luar cakupan |

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
| `array` + `items` bertipe T | `List<T>`, T memakai wrapper (`List<Integer>`, bukan `List<int>`) |
| `array` + `items` object | `List<NamaClass>`, dan class dibuat terpisah |
| `enum` | satu `enum` terpisah |
| nested object | class terpisah, dipakai sebagai tipe field |
| `$ref: "#/$defs/X"` | tipe `X`, class atau enum `X` dibuat dari definisi di `$defs` |

Array tidak punya primitif/wrapper: elemennya selalu wrapper dan field `List<T>`
tidak berubah walau required atau tidak.

---

## 4. Aturan penamaan

### 4.1 Nama class dan enum (PascalCase)

| Sumber | Nama Java |
|---|---|
| root schema | dari `title` bila ada, kalau tidak `Root` **[konfirmasi]** |
| property bertipe nested object atau enum | nama property → PascalCase. `profile` → `Profile` |
| item array berupa object | nama property → PascalCase. `addresses` → `Addresses` **[konfirmasi]** |
| entri di `$defs` | nama kuncinya apa adanya → PascalCase. `Address` → `Address` |

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
2. Gabungkan sesuai gaya: PascalCase, camelCase, atau UPPER_SNAKE_CASE.
3. Kalau hasil diawali angka, tambahkan `_` di depan.

### 4.5 Reserved word dan bentrok

Compiler **tidak mengubah diam-diam** nama yang bermasalah. Nama yang menjadi
reserved word Java (`class`, `int`, `default`, dan lainnya), atau dua nama yang
bentrok setelah dikonversi (`first-name` dan `first_name` sama-sama menjadi
`firstName`), dilaporkan sebagai error semantic.

---

## 5. Pemetaan error semantic (usulan kode)

Kode final ditetapkan di `error_codes.md`. Di sini hanya hubungan aturan dan
kodenya.

| Kode | Kondisi | Contoh |
|---|---|---|
| E201 | `$ref` menunjuk ke definisi yang tidak ada | `"$ref": "#/$defs/Foo"` tetapi `Foo` tidak ada |
| E202 | nama di `required` tidak ada di `properties` | `"required": ["email"]` tanpa property `email` |
| E203 | nilai `type` tidak dikenal | `"type": "text"` |
| E204 | nama bentrok atau reserved word Java | property bernama `class` |

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
    "status":  { "enum": ["active", "in-progress"] },
    "tags":    { "type": "array", "items": { "type": "string" } },
    "address": { "$ref": "#/$defs/Address" },
    "profile": {
      "type": "object",
      "properties": { "bio": { "type": "string" } }
    }
  },
  "required": ["name", "age"],
  "$defs": {
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
EnumIR Status
  - ACTIVE   (json: "active")
  - IN_PROGRESS   (json: "in-progress")
ClassIR Profile
  - bio: String
ClassIR Address
  - city: String [required]
ClassIR User
  - name: String [required]
  - age: int [required]
  - status: Status
  - tags: List<String>
  - address: Address
  - profile: Profile
```

Perhatikan `age` menjadi `int` karena required, sedangkan `status` bukan
required sehingga tidak ada pengaruh primitif/wrapper (tipenya enum).

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

1. Nama class root: `title` dengan cadangan `Root`.
2. Nama class item array berupa object: sama dengan nama property.
3. Output class hanya `private` field + getter + setter (tanpa constructor,
   `toString`, dan sebagainya).
4. Semua file di default package (tanpa baris `package`).
5. Kode error E201 sampai E204 dan penomorannya.