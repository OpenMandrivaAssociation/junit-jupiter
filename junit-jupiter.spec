Name:		junit-jupiter
Version:	6.0.3
Release:	1
Summary:	JUnit Jupiter API, engine, and parameterized tests
Group:		Development/Java
License:	EPL-2.0
URL:		https://junit.org/junit5/
Source0:	junit-framework-%{version}.tar.gz
Source1:	junit-jupiter-gen-jre.py
Patch0:		junit-jupiter-6.0.3-system-fastcsv.patch

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	python
BuildRequires:	jmod(org.jspecify)
BuildRequires:	mvn(org.jspecify:jspecify) = 1.0.0
BuildRequires:	mvn(org.apiguardian:apiguardian-api) = 1.1.2
BuildRequires:	mvn(org.opentest4j:opentest4j) = 1.3.0
BuildRequires:	mvn(org.junit.platform:junit-platform-commons) = %{version}
BuildRequires:	mvn(org.junit.platform:junit-platform-engine) = %{version}
BuildRequires:	mvn(org.junit.platform:junit-platform-launcher) = %{version}
BuildRequires:	mvn(de.siegmar:fastcsv) = 4.1.0
BuildRequires:	mvn(org.jetbrains.kotlin:kotlin-stdlib)
Requires:	jmod(org.jspecify)
Requires:	mvn(org.jspecify:jspecify) = 1.0.0
Requires:	mvn(org.apiguardian:apiguardian-api) = 1.1.2
Requires:	mvn(org.opentest4j:opentest4j) = 1.3.0
Requires:	mvn(org.junit.platform:junit-platform-commons) = %{version}
Requires:	mvn(org.junit.platform:junit-platform-engine) = %{version}
Requires:	mvn(de.siegmar:fastcsv) = 4.1.0

%description
JUnit Jupiter %{version} API, engine, and parameterized-test extension.
Gradle 9.9.1 asks the build for junit-jupiter %{version}. Platform
commons, engine, and launcher stay in junit6, as versioned side jars.
Upstream shades FastCSV into junit-jupiter-params. This package requires
the system fastcsv jar instead, and the params module reads it. The two
Kotlin extension sources are not compiled: kotlinc 2.0.21 aborts while
parsing this JDK's java.version and never reads the files. JRE.java is
generated from the upstream jre.yaml list, which stops at Java 26.

%prep
%autosetup -n junit-framework-r%{version} -p1
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
find . -type d -name '*.jar' -print >> binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi
python %{SOURCE1} .
grep -F -q 'JAVA_26(26)' junit-jupiter-api/src/main/java/org/junit/jupiter/api/condition/JRE.java
grep -F -q 'case 26 -> JAVA_26;' junit-jupiter-api/src/main/java/org/junit/jupiter/api/condition/JRE.java
grep -F -q 'MINIMUM_VERSION = 8' junit-jupiter-api/src/main/java/org/junit/jupiter/api/condition/JRE.java
if grep -F -q 'case 27 ->' junit-jupiter-api/src/main/java/org/junit/jupiter/api/condition/JRE.java; then
	exit 1
fi
grep -F -q 'requires de.siegmar.fastcsv;' junit-jupiter-params/src/main/java/module-info.java

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
SYS=%{_javadir}
for jar in \
	apiguardian-api.jar \
	jspecify.jar \
	opentest4j/opentest4j.jar \
	junit-platform-commons-%{version}.jar \
	junit-platform-engine-%{version}.jar \
	junit-platform-launcher-%{version}.jar \
	kotlin-stdlib.jar \
	fastcsv.jar
do
	test -s "$SYS/$jar"
done
desc=$(jar --describe-module --file "$SYS/jspecify.jar")
if ! printf '%%s\n' "$desc" | grep -F -q 'org.jspecify'; then
	printf '%%s\n' "$desc"
	exit 1
fi
test "$(find junit-jupiter-api/src/main/kotlin -name '*.kt' | wc -l)" -eq 1
test "$(find junit-jupiter-params/src/main/kotlin -name '*.kt' | wc -l)" -eq 1
MP="$SYS/apiguardian-api.jar:$SYS/jspecify.jar:$SYS/opentest4j/opentest4j.jar:$SYS/junit-platform-commons-%{version}.jar:$SYS/junit-platform-engine-%{version}.jar:$SYS/kotlin-stdlib.jar:$SYS/fastcsv.jar"

compile_java() {
	mod=$1
	mp=$2
	expect=$3
	mkdir -p "classes/$mod"
	find "$mod/src/main/java" -name '*.java' > "$mod.list"
	test "$(wc -l < "$mod.list")" -eq "$expect"
	javac --release 17 --module-version %{version} -encoding UTF-8 -Xlint:-options,-removal -proc:none \
		--module-path "$mp" -d "classes/$mod" @"$mod.list"
	if [ -d "$mod/src/main/resources" ]; then
		cp -a "$mod/src/main/resources/." "classes/$mod/"
	fi
	jar cf "$mod.jar" -C "classes/$mod" .
	jar i "$mod.jar"
}

compile_java junit-jupiter-api "$MP" 170
compile_java junit-jupiter-engine "$MP:junit-jupiter-api.jar" 121
compile_java junit-jupiter-params "$MP:junit-jupiter-api.jar" 95
mkdir -p classes/junit-jupiter
javac --release 17 --module-version %{version} -encoding UTF-8 -proc:none \
	--module-path "junit-jupiter-api.jar:junit-jupiter-engine.jar:junit-jupiter-params.jar:$MP" \
	-d classes/junit-jupiter \
	junit-jupiter/src/main/java/module-info.java
jar cf junit-jupiter.jar -C classes/junit-jupiter .
jar i junit-jupiter.jar

javap -v -classpath junit-jupiter-api.jar org.junit.jupiter.api.condition.JRE | grep -F -q 'major version: 61'
jar tf junit-jupiter-engine.jar | grep -F -q 'META-INF/services/org.junit.platform.engine.TestEngine'
for pair in \
	'org.junit.jupiter.api junit-jupiter-api.jar' \
	'org.junit.jupiter.engine junit-jupiter-engine.jar' \
	'org.junit.jupiter.params junit-jupiter-params.jar' \
	'org.junit.jupiter junit-jupiter.jar'
do
	mod=${pair%%%% *}
	file=${pair##* }
	desc=$(jar --describe-module --file "$file")
	if ! printf '%%s\n' "$desc" | grep -F -q "$mod@%{version}"; then
		printf '%%s\n' "$desc"
		exit 1
	fi
	if printf '%%s\n' "$desc" | grep -F -q 'Unable'; then
		printf '%%s\n' "$desc"
		exit 1
	fi
done
params_desc=$(jar --describe-module --file junit-jupiter-params.jar)
if ! printf '%%s\n' "$params_desc" | grep -F -q 'de.siegmar.fastcsv'; then
	printf '%%s\n' "$params_desc"
	exit 1
fi

write_pom() {
	file=$1
	artifact=$2
	deps=$3
	cat > "$file" <<END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>org.junit.jupiter</groupId>
  <artifactId>$artifact</artifactId>
  <version>%{version}</version>
  <name>$artifact</name>
  <description>JUnit Jupiter $artifact %{version}.</description>
  <url>https://junit.org/junit5/</url>
  <licenses>
    <license>
      <name>EPL-2.0</name>
      <url>https://www.eclipse.org/legal/epl-2.0/</url>
      <distribution>repo</distribution>
    </license>
  </licenses>
$deps
</project>
END
}
opt_dep() {
	printf '    <dependency>\n      <groupId>%%s</groupId>\n      <artifactId>%%s</artifactId>\n      <version>%%s</version>\n      <optional>true</optional>\n    </dependency>\n' "$1" "$2" "$3"
}
req_dep() {
	scope=$4
	printf '    <dependency>\n      <groupId>%%s</groupId>\n      <artifactId>%%s</artifactId>\n      <version>%%s</version>\n' "$1" "$2" "$3"
	if [ -n "$scope" ]; then
		printf '      <scope>%%s</scope>\n' "$scope"
	fi
	printf '    </dependency>\n'
}
deps_open='  <dependencies>'
deps_close='  </dependencies>'
{
	printf '%%s\n' "$deps_open"
	req_dep org.junit.platform junit-platform-commons %{version} ''
	req_dep org.opentest4j opentest4j 1.3.0 ''
	opt_dep org.apiguardian apiguardian-api 1.1.2
	opt_dep org.jspecify jspecify 1.0.0
	printf '%%s\n' "$deps_close"
} > api.deps
{
	printf '%%s\n' "$deps_open"
	req_dep org.junit.platform junit-platform-engine %{version} ''
	req_dep org.junit.platform junit-platform-commons %{version} ''
	req_dep org.junit.jupiter junit-jupiter-api %{version} ''
	req_dep org.opentest4j opentest4j 1.3.0 ''
	opt_dep org.apiguardian apiguardian-api 1.1.2
	opt_dep org.jspecify jspecify 1.0.0
	printf '%%s\n' "$deps_close"
} > engine.deps
{
	printf '%%s\n' "$deps_open"
	req_dep org.junit.jupiter junit-jupiter-api %{version} ''
	req_dep org.junit.platform junit-platform-commons %{version} ''
	req_dep de.siegmar fastcsv 4.1.0 ''
	opt_dep org.apiguardian apiguardian-api 1.1.2
	opt_dep org.jspecify jspecify 1.0.0
	printf '%%s\n' "$deps_close"
} > params.deps
{
	printf '%%s\n' "$deps_open"
	req_dep org.junit.jupiter junit-jupiter-api %{version} ''
	req_dep org.junit.jupiter junit-jupiter-params %{version} ''
	req_dep org.junit.jupiter junit-jupiter-engine %{version} runtime
	printf '%%s\n' "$deps_close"
} > agg.deps
write_pom junit-jupiter-api.pom junit-jupiter-api "$(cat api.deps)"
write_pom junit-jupiter-engine.pom junit-jupiter-engine "$(cat engine.deps)"
write_pom junit-jupiter-params.pom junit-jupiter-params "$(cat params.deps)"
write_pom junit-jupiter.pom junit-jupiter "$(cat agg.deps)"
grep -F -q '<version>%{version}</version>' junit-jupiter.pom
grep -F -q '<artifactId>fastcsv</artifactId>' junit-jupiter-params.pom
grep -F -q '<scope>runtime</scope>' junit-jupiter.pom

%install
set -eo pipefail
: > .mfiles
pin_side() {
	mod=$1
	sysjar install --buildroot %{buildroot} \
		--artifact "$mod.pom:$mod.jar" \
		--file-name "$mod-%{version}" \
		--filelist ".mfiles-$mod"
	index="%{buildroot}/usr/share/sysjar/index/org.junit.jupiter/${mod}.sysjar"
	test -f "$index"
	/bin/mv "$index" "%{buildroot}/usr/share/sysjar/index/org.junit.jupiter/${mod}-%{version}.sysjar"
	sed -i "s|/usr/share/sysjar/index/org.junit.jupiter/${mod}\\.sysjar|/usr/share/sysjar/index/org.junit.jupiter/${mod}-%{version}.sysjar|" ".mfiles-$mod"
	grep -F -q '"version": "%{version}"' "%{buildroot}/usr/share/sysjar/index/org.junit.jupiter/${mod}-%{version}.sysjar"
	while IFS= read -r line; do
		grep -qxF -- "$line" .mfiles || printf '%%s\n' "$line" >> .mfiles
	done < ".mfiles-$mod"
}
pin_side junit-jupiter-api
pin_side junit-jupiter-engine
pin_side junit-jupiter-params
pin_side junit-jupiter
grep -F -q 'junit-jupiter-%{version}.jar' .mfiles
if grep -E -q '/junit-jupiter(-api|-engine|-params)?\.sysjar$' .mfiles; then
	exit 1
fi

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:$PATH"
SYS=%{_javadir}
JUP=%{buildroot}%{_javadir}
for jar in \
	"$JUP/junit-jupiter-api-%{version}.jar" \
	"$JUP/junit-jupiter-engine-%{version}.jar" \
	"$JUP/junit-jupiter-params-%{version}.jar" \
	"$JUP/junit-jupiter-%{version}.jar"
do
	test -s "$jar"
done
MP="$JUP/junit-jupiter-api-%{version}.jar:$JUP/junit-jupiter-engine-%{version}.jar:$JUP/junit-jupiter-params-%{version}.jar:$JUP/junit-jupiter-%{version}.jar:$SYS/junit-platform-launcher-%{version}.jar:$SYS/junit-platform-commons-%{version}.jar:$SYS/junit-platform-engine-%{version}.jar:$SYS/apiguardian-api.jar:$SYS/jspecify.jar:$SYS/opentest4j/opentest4j.jar:$SYS/kotlin-stdlib.jar:$SYS/fastcsv.jar"
mkdir -p check
cat > check/Smoke.java << 'EOF'
import java.io.PrintWriter;
import java.io.StringWriter;
import org.junit.jupiter.api.condition.JRE;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.platform.engine.discovery.DiscoverySelectors;
import org.junit.platform.launcher.Launcher;
import org.junit.platform.launcher.TestIdentifier;
import org.junit.platform.launcher.TestPlan;
import org.junit.platform.launcher.core.LauncherDiscoveryRequestBuilder;
import org.junit.platform.launcher.core.LauncherFactory;
import org.junit.platform.launcher.listeners.SummaryGeneratingListener;
import org.junit.platform.launcher.listeners.TestExecutionSummary;

public class Smoke {
	@ParameterizedTest
	@CsvSource("gradle,6")
	void csv(String name, int major) {
		if (!"gradle".equals(name) || major != 6) {
			throw new AssertionError(name + " " + major);
		}
	}

	@SuppressWarnings("removal")
	public static void main(String[] args) {
		int feature = Runtime.version().feature();
		JRE jre = JRE.currentJre();
		JRE expected = (feature >= 8 && feature <= 26) ? JRE.valueOf("JAVA_" + feature) : JRE.OTHER;
		if (jre != expected || JRE.currentVersionNumber() != feature) {
			throw new AssertionError(jre + " feature " + feature);
		}
		if (JRE.JAVA_8.version() != 8 || JRE.JAVA_17.version() != 17 || JRE.JAVA_26.version() != 26) {
			throw new AssertionError("JRE constants");
		}
		if (JRE.OTHER.version() != Integer.MAX_VALUE) {
			throw new AssertionError("OTHER");
		}
		var request = LauncherDiscoveryRequestBuilder.request()
			.selectors(DiscoverySelectors.selectClass(Smoke.class))
			.build();
		Launcher launcher = LauncherFactory.create();
		TestPlan plan = launcher.discover(request);
		boolean sawEngine = false;
		for (TestIdentifier id : plan.getRoots()) {
			if (id.getUniqueId().contains("[engine:junit-jupiter]")) {
				sawEngine = true;
			}
		}
		if (!sawEngine) {
			throw new AssertionError(plan.getRoots().toString());
		}
		SummaryGeneratingListener listener = new SummaryGeneratingListener();
		launcher.execute(request, listener);
		TestExecutionSummary summary = listener.getSummary();
		if (summary.getTestsSucceededCount() != 1 || summary.getTestsFailedCount() != 0) {
			StringWriter sw = new StringWriter();
			summary.printFailuresTo(new PrintWriter(sw));
			System.out.println(sw);
			throw new AssertionError("tests " + summary.getTestsSucceededCount());
		}
		System.out.println(args[0] + " " + jre.name() + " " + feature + " junit-jupiter " + summary.getTestsSucceededCount());
	}
}
EOF
javac --release 17 -encoding UTF-8 -Xlint:-options,-removal -proc:none \
	--module-path "$MP" \
	--add-modules org.junit.jupiter.params,org.junit.jupiter.engine,org.junit.platform.launcher \
	-d check check/Smoke.java
java --module-path "$MP" \
	--add-modules org.junit.jupiter.params,org.junit.jupiter.engine,org.junit.platform.launcher \
	-cp check Smoke jupiter_ok > check.log
cat check.log
grep -E -q '^jupiter_ok (JAVA_([8-9]|1[0-9]|2[0-6])|OTHER) [0-9]+ junit-jupiter 1$' check.log

%files -f .mfiles
%doc README.md
%license LICENSE.md
