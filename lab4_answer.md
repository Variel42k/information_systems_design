# Отчёт: проверка примеров из статьи «FindBugs помогает узнать Java лучше»

Источник: Тагир Валеев, Хабр, 9 ноября 2013 — «FindBugs помогает узнать Java лучше». Ключевые примеры и формулировки взяты из публикации. В работе использован современный форк **SpotBugs** (наследник FindBugs) и плагин **fb-contrib** для дополнительных диагностик.

---

## Инструменты и конфигурация

- **SpotBugs 4.x** (форк FindBugs) — стандартные детекторы.  
- **sb-contrib (fb-contrib для SpotBugs)** — дополнительные детекторы (в т.ч. для `BigDecimal.equals`).

Пример `build.gradle` для воспроизведения локально:
```groovy
plugins {
  id 'java'
  id 'com.github.spotbugs' version '6.0.18' // актуальную версию смотрите на Gradle Portal
}

repositories { mavenCentral() }

dependencies {
  testImplementation 'org.junit.jupiter:junit-jupiter:5.11.0'
  // Плагин расширенных детекторов
  spotbugsPlugins 'com.mebigfatguy:sb-contrib:7.6.15'
}

tasks.withType(com.github.spotbugs.snom.SpotBugsTask).configureEach {
  reports.create("html") {
    required = true
    outputLocation = file("$buildDir/reports/spotbugs/spotbugs.html")
    stylesheet = 'fancy-hist.xsl'
  }
}
```
О проекте SpotBugs и детекторах: офиц. сайт и документация. О fb-contrib: список детекторов и репозиторий.

---

## 1) Тернарный оператор `?:` против `if/else` и приведение типов

### Исходные фрагменты из статьи
```java
Type var = condition ? valTrue : valFalse;
```
```java
Type var;
if (condition)
  var = valTrue;
else
  var = valFalse;
```
```java
Number n = flag ? new Integer(1) : new Double(2.0);
```

### Демонстрационная программа
```java
public class Ex1_Ternary {
    public static void main(String[] args) {
        boolean flag = Boolean.parseBoolean(args.length > 0 ? args[0] : "true");
        Number n = flag ? new Integer(1) : new Double(2.0);
        System.out.println(n + " (" + n.getClass().getSimpleName() + ")");
    }
}
```

### Ожидаемый вывод
- При `flag=true`: `1.0 (Double)` — несмотря на `new Integer(1)`, результат — **Double 1.0**.
- При `flag=false`: `2.0 (Double)`.

### Что скажет SpotBugs
- **BX_UNBOXED_AND_COERCED_FOR_TERNARY_OPERATOR** — «значения-обёртки распакованы и приведены к общему примитивному типу при вычислении тернарного оператора, затем снова упакованы».
- **DM_NUMBER_CTOR / DM_BOXED_PRIMITIVE_TOSTRING** и пр. — замечания об избыточном создании `new Integer/Double`, предпочтении `valueOf` и т.п.

### Версия без проблем
```java
public class Ex1_Fixed {
    public static void main(String[] args) {
        boolean flag = Boolean.parseBoolean(args.length > 0 ? args[0] : "true");
        Number n = flag ? 1.0 : 2.0; // автоупаковка в Double
        System.out.println(n);
    }
}
```

---

## 2) Тернарный с `null` и «гарантированный» NPE во вложенном варианте

### Исходные фрагменты из статьи
```java
Integer n = flag ? 1 : null;
```
```java
Integer n = flag1 ? 1 : flag2 ? 2 : null;
```
Эквивалент раскрытия:
```java
Integer n;
if (flag1)
    n = Integer.valueOf(1);
else {
    if (flag2)
        n = Integer.valueOf(Integer.valueOf(2).intValue());
    else
        n = Integer.valueOf(((Integer) null).intValue());
}
```

### Демонстрационная программа
```java
public class Ex2_NullTernary {
    static Integer nested(boolean flag1, boolean flag2) {
        return flag1 ? 1 : flag2 ? 2 : null; // опасно
    }
    public static void main(String[] args) {
        System.out.println(nested(true, false));   // 1
        System.out.println(nested(false, true));   // 2
        System.out.println(nested(false, false));  // может привести к NPE при дальнейшем распаковывании
    }
}
```

### Ожидаемый эффект
- Само присваивание скомпилируется, но последующая **распаковка в `int`** приведёт к `NullPointerException` на пути `false,false`.

### Что скажет SpotBugs
- **NP_NULL_ON_SOME_PATH** — «возможная разыменовка null на некоторых путях исполнения».
- **BX_UNBOXING_IMMEDIATELY_REBOXED** — «распаковка сразу за которой следует повторная упаковка» (для развернутого эквивалента).

### Безопасные альтернативы
```java
// Явный if/else
Integer safe1(boolean f1, boolean f2) {
    if (f1) return 1;
    if (f2) return 2;
    return null; // документируйте возможность null
}

// Или возвращаем примитив и «сентинел»
int safe2(boolean f1, boolean f2) {
    if (f1) return 1;
    if (f2) return 2;
    return Integer.MIN_VALUE; // или OptionalInt/Optional<Integer>
}
```

---

## 3) Возврат `null` для примитива `double`

### Исходник из статьи
```java
double[] vals = new double[] {1.0, 2.0, 3.0};
double getVal(int idx) {
    return (idx < 0 || idx >= vals.length) ? null : vals[idx];
}
```

### Проблема
Метод возвращает **примитив `double`**, вернуть `null` невозможно — но компилируется из-за правил вывода типа у тернарного оператора. `null` «подтягивает» выражение к ссылочному типу `Double`, затем нужно привести к `double` ⇒ NPE при выполнении на недопустимом индексе.

### Репродукция
```java
public class Ex3_PrimitiveNull {
    static final double[] vals = {1.0, 2.0, 3.0};
    static double getVal(int idx) {
        return (idx < 0 || idx >= vals.length) ? null : vals[idx]; // компилируется, но аварийно
    }
    public static void main(String[] args) { System.out.println(getVal(-1)); }
}
```

### Что скажет SpotBugs
- **NP_TOSTRING_COULD_RETURN_NULL / NP_NULL_ON_SOME_PATH**– семейство предупреждений о возможном NPE на ветке.
- Главная идея: «примитив не может быть `null`; тернарий создаёт путь с распаковкой `null`».

### Исправления
```java
// Возвращать-обёртку и null
static Double getValBoxed(int idx) {
    return (idx < 0 || idx >= vals.length) ? null : vals[idx];
}
// Или NaN/исключение/OptionalDouble
static double getValOrNaN(int idx) {
    return (idx < 0 || idx >= vals.length) ? Double.NaN : vals[idx];
}
```

---

## 4) DateFormat и потокобезопасность

### Исходники из статьи
```java
public String getDate() {
    return new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new java.util.Date());
}
```
Оптимизация «в лоб» (плохо в многопоточности):
```java
private static final java.text.DateFormat FORMAT = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
public String getDate() {
    return FORMAT.format(new java.util.Date());
}
```

### Проблема
`SimpleDateFormat` **не потокобезопасен**; общий статический экземпляр может выдавать некорректные строки при параллельном использовании.

### Что скажет SpotBugs
- **STCAL_INVOKE_ON_STATIC_DATE_FORMAT_INSTANCE** — «вызов метода статического экземпляра `DateFormat`».

### Рекомендованные решения
```java
// Современный подход (java.time) — потокобезопасно
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
class Ex4_Date {
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    static String getDate() { return LocalDateTime.now().format(FMT); }
}
```

---

## 5) Подводные камни BigDecimal

### Исходник из статьи
```java
System.out.println(new java.math.BigDecimal(1.1));
```
Ожидаемый вывод: «грязное» десятичное представление `double` 1.1 (IEEE 754), например `1.1000000000000000888...`

### Что скажет SpotBugs
- **DMI_BIGDECIMAL_CONSTRUCTED_FROM_DOUBLE** — «BigDecimal создан из double; возможна потеря точности; используйте строку или `BigDecimal.valueOf(double)`».

### Исправление
```java
import java.math.BigDecimal;
class Ex5_BigDecimalCtor {
    public static void main(String[] args) {
        System.out.println(new BigDecimal("1.1"));
        System.out.println(BigDecimal.valueOf(1.1)); // корректная интерпретация
    }
}
```

### Равенство BigDecimal
Исходник:
```java
BigDecimal d1 = new BigDecimal("1.1");
BigDecimal d2 = new BigDecimal("1.10");
System.out.println(d1.equals(d2)); // false
```
- `equals` учитывает **шкалу** (scale), поэтому `1.1` и `1.10` не равны по `equals`, но `d1.compareTo(d2) == 0`.

Доп. диагностика (из **fb-contrib**):
- **MDM_BIGDECIMAL_EQUALS** — «использование `equals` для сравнения `BigDecimal` — обычно ошибка; используйте `compareTo`».

---

## 6) Переводы строк и `printf`

### Исходник из статьи
```java
System.out.printf("%s\n", "str#1");
System.out.println("str#2");
```
Проблема: в форматной строке `\n` — это всегда LF, а `println` использует системный перевод строки. В одном потоке получится смесь `\n` и платформенного `line.separator`.

### Что скажет SpotBugs
- **VA_FORMAT_STRING_USES_NEWLINE** — «в форматной строке следует использовать `%n` вместо `\n` для платформенно-зависимого перевода строки».

### Исправление
```java
System.out.printf("%s%n%s%n", "str#1", "str#2");
// или просто
System.out.println("str#1");
System.out.println("str#2");
```

---

# Приложение: Полные минимальные примеры (по классам)

Для удобства запуска каждый пример можно разместить в отдельном классе `public class ExN_...` и собрать простым `javac`. Организация по папкам не принципиальна.

- `Ex1_Ternary.java`, `Ex1_Fixed.java`
- `Ex2_NullTernary.java`
- `Ex3_PrimitiveNull.java`
- `Ex4_Date.java`
- `Ex5_BigDecimalCtor.java`
- `Ex6_Newline.java`

---

## Ожидаемые предупреждения (сводно)

| Пример | Детекторы (ключи) | Суть |
|---|---|---|
| Ex1_Ternary | BX_UNBOXED_AND_COERCED_FOR_TERNARY_OPERATOR; DM_NUMBER_CTOR | Тернарий приводит обёртки к общему примитиву; избыточные конструкторы |
| Ex2_NullTernary | NP_NULL_ON_SOME_PATH; BX_UNBOXING_IMMEDIATELY_REBOXED | Возможная распаковка `null`; избыточная упаковка/распаковка |
| Ex3_PrimitiveNull | NP_* (ветки к NPE при распаковке) | Возврат `null` при ожидаемом `double` |
| Ex4_Date | STCAL_INVOKE_ON_STATIC_DATE_FORMAT_INSTANCE | Статический `DateFormat` не потокобезопасен |
| Ex5_BigDecimalCtor | DMI_BIGDECIMAL_CONSTRUCTED_FROM_DOUBLE; (fb-contrib) MDM_BIGDECIMAL_EQUALS | Конструктор из `double`; для сравнения — `compareTo` |
| Ex6_Newline | VA_FORMAT_STRING_USES_NEWLINE | В `printf` используйте `%n` вместо `\n` |

---

## Примечания по спецификации языка

- Поведение тернарного оператора и вывод общего типа описаны в JLS §15.25. Именно оно приводит к распаковке и приведению типов ещё до присваивания.

### 1️⃣ Класс Book
public class Book {
    private @Nonnull String author;
    private @Nonnull String title;
    private @CheckForNull String subtitle;

    public @Nonnull String getAuthor() { return author; }
    public @Nonnull String getSubtitle() { return subtitle; }
    public @Nonnull String getTitle() { return title; }
}
⚠️ FindBugs предупреждения:
(1) NP_NONNULL_FIELD_NOT_INITIALIZED_IN_CONSTRUCTOR
Поля author и title помечены как @Nonnull, но не инициализированы ни в конструкторе, ни при объявлении.
📖 Объяснение:
FindBugs понимает, что @Nonnull означает «никогда не должно быть null».
Так как в классе нет конструктора, и поля не получают значения при объявлении, это означает, что после создания new Book(), author и title будут null.
Это противоречит контракту @Nonnull.
✅ Исправление:
Добавить конструктор и инициализацию:
public Book(@Nonnull String author, @Nonnull String title, @CheckForNull String subtitle) {
    this.author = author;
    this.title = title;
    this.subtitle = subtitle;
}
________________________________________
(2) NP_METHOD_RETURN_RELAXING_ANNOTATION
Метод getSubtitle() объявлен как @Nonnull, но возвращает поле @CheckForNull subtitle.
📖 Объяснение:
subtitle может быть null, но getSubtitle() заявляет, что возвращает @Nonnull.
Это явное нарушение null-контракта.
✅ Исправление:
public @CheckForNull String getSubtitle() {
    return subtitle;
}
________________________________________
### 2️⃣ Класс Library
public class Library {
    private final Set<Book> books = new TreeSet<Book>(new ComparatorImpl());
    
    public void addBook(@Nonnull Book newBook) {
        if (newBook == null) return;
        books.add(newBook);
    }

    public @Nonnull Iterable<? extends String> describeBooksBy(@Nonnull String author) {
        List<String> result = new ArrayList<String>();
        for (Book b : books) {
            if (!author.equals(b.getAuthor())) continue;
            result.add(String.format("%s: %d", b.getAuthor(), b.getTitle()));
        }
        return result;
    }

    private static class ComparatorImpl implements Comparator<Book>, Serializable {
        @Override public int compare(Book o1, Book o2) {
            int r = o1.getAuthor().compareTo(o2.getAuthor());
            if (r != 0) return r;
            r = o1.getTitle().compareTo(o2.getTitle());
            if (r != 0) return r;
            r = o1.getSubtitle().compareTo(o2.getSubtitle());
            return 0;
        }
        private static final long serialVersionUID = 0L;
    }
}
________________________________________
⚠️ FindBugs предупреждения:
(3) NP_NULL_PARAM_DEREF_NONVIRTUAL
В методе ComparatorImpl.compare() вызывается o1.getSubtitle().compareTo(o2.getSubtitle()), хотя getSubtitle() может вернуть null.
📖 Объяснение:
Book.getSubtitle() возвращает @CheckForNull String, поэтому compareTo() может вызвать NullPointerException.
FindBugs отметит это как потенциальное разыменование null.
✅ Исправление:
String s1 = o1.getSubtitle();
String s2 = o2.getSubtitle();
if (s1 == null && s2 == null) return 0;
if (s1 == null) return -1;
if (s2 == null) return 1;
return s1.compareTo(s2);
________________________________________
(4) FORMAT_STRING_INVALID
В строке String.format("%s: %d", b.getAuthor(), b.getTitle());
используется формат %d, но b.getTitle() возвращает String, а не число.
📖 Объяснение:
%d ожидает int, Integer, long и т.д.
Передаётся String, что вызовет IllegalFormatConversionException во время выполнения.
✅ Исправление:
result.add(String.format("%s: %s", b.getAuthor(), b.getTitle()));
________________________________________
(5) NP_PARAMETER_MUST_BE_NONNULL_BUT_MARKED_AS_NULLABLE (возможное предупреждение)
В методе addBook(@Nonnull Book newBook) проверяется if (newBook == null).
FindBugs может выдать предупреждение: «Зачем проверять null у параметра, который аннотирован @Nonnull?»
📖 Объяснение:
Технически — проверка допустима, если проект хочет быть совместим с клиентами без аннотаций, но FindBugs считает это “redundant null check”.
✅ Можно либо:
•	убрать @Nonnull, либо
•	оставить комментарий (что уже сделано) — FindBugs тогда не будет считать это ошибкой, а только предупреждением.

Задание 3. Библиотека colt

Bug 1 — EQ_CLASS_NEQ_HASHCODE

Class: cern.colt.matrix.DoubleMatrix2D
Category: CORRECTNESS
Pattern: EQ_CLASS_NEQ_HASHCODE
Description:
Класс переопределяет метод equals(Object) без соответствующего переопределения hashCode().
Это нарушает контракт между equals() и hashCode(): объекты, которые равны по equals, должны иметь одинаковые hashCode.
При использовании таких объектов в HashMap или HashSet возможны логические ошибки (невозможность найти элемент, дублирование и т.д.).

Recommendation (Fix):
Добавить реализацию hashCode(), согласованную с equals(). Например:

@Override
public int hashCode() {
    int h = 1;
    for (int i = 0; i < rows(); i++)
        for (int j = 0; j < columns(); j++)
            h = 31 * h + Double.hashCode(getQuick(i, j));
    return h;
}

Bug 2 — IS2_INCONSISTENT_SYNC

Class: cern.colt.matrix.impl.DenseDoubleMatrix2D
Category: MT_CORRECTNESS
Pattern: IS2_INCONSISTENT_SYNC
Description:
Некоторые поля (elements, rows, columns) изменяются без синхронизации, при этом методы класса используются из разных потоков.
Это создаёт гонки данных и может приводить к неконсистентным состояниям матриц при параллельных операциях.

Recommendation (Fix):

Либо документировать, что класс не является потокобезопасным (и синхронизацию должен обеспечивать вызывающий код).

Либо синхронизировать доступ к полям или использовать java.util.concurrent механизмы (например, ReentrantLock).