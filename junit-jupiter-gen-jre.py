#!/usr/bin/python
"""Expand junit-jupiter-api's JRE.java.jte inputs without the jte library.

The template parameters come from GenerateJreRelatedSourceCode: every entry
in jre.yaml, minRuntimeVersion 17, and the Eclipse license header.
"""
import sys
from pathlib import Path


def parse_jres(text):
    jres = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- version:"):
            if current is not None:
                jres.append(current)
            current = {"version": int(line.split(":", 1)[1].strip()), "since": None}
        elif line.startswith("since:"):
            if current is None:
                raise SystemExit("since before version in jre.yaml")
            current["since"] = line.split(":", 1)[1].strip().strip("'\"")
        else:
            raise SystemExit("unrecognized jre.yaml line: " + line)
    if current is not None:
        jres.append(current)
    return jres


def const_block(jre, min_runtime):
    version = jre["version"]
    since = jre["since"]
    lines = ["\t/**", "\t * Java %d." % version]
    if since is not None or version < min_runtime:
        lines.append("\t *")
    if since is not None:
        lines.append("\t * @since %s" % since)
    if version < min_runtime:
        lines.append("\t * @deprecated No longer supported at runtime; please use {@link #JAVA_17} or later")
    lines.append("\t */")
    if version < min_runtime:
        lines.append('\t@API(status = DEPRECATED, since = "6.0")')
        lines.append('\t@Deprecated(since = "6.0", forRemoval = true)')
    elif since is not None:
        lines.append('\t@API(status = STABLE, since = "%s")' % since)
    lines.append("\tJAVA_%d(%d)," % (version, version))
    return "\n".join(lines)


def render(jres, header, min_runtime):
    if not header.endswith("\n"):
        header += "\n"
    see = "\n".join(" * @see #JAVA_%d" % jre["version"] for jre in jres)
    constants = "\n\n".join(const_block(jre, min_runtime) for jre in jres)
    cases = "\n".join("\t\t\tcase %d -> JAVA_%d;" % (jre["version"], jre["version"]) for jre in jres)
    other_links = ", ".join("{@link #JAVA_%d}" % jre["version"] for jre in jres)
    minimum = jres[0]["version"]
    return """{header}package org.junit.jupiter.api.condition;

import static org.apiguardian.api.API.Status.DEPRECATED;
import static org.apiguardian.api.API.Status.MAINTAINED;
import static org.apiguardian.api.API.Status.STABLE;

import org.apiguardian.api.API;

/**
 * Enumeration of Java Runtime Environment (JRE) versions.
 *
 * <p>If the current JRE version can be detected but is not one of the predefined
 * constants in this enum, {{@link #OTHER}} will be considered to be the
 * {{@linkplain #isCurrentVersion current JRE version}}.
 *
 * @since 5.1
{see}
 * @see #OTHER
 * @see EnabledOnJre
 * @see DisabledOnJre
 * @see EnabledForJreRange
 * @see DisabledForJreRange
 */
@API(status = STABLE, since = "5.1")
public enum JRE {{

	/**
	 * An undefined JRE version.
	 *
	 * <p>This constant is used by JUnit as a default configuration value but is
	 * not intended to be used by users.
	 *
	 * <p>This constant returns {{@code -1}} for its {{@linkplain #version() version}}.
	 *
	 * @since 5.12
	 */
	@API(status = MAINTAINED, since = "5.13.3")
	UNDEFINED(-1),

{constants}

	/**
	 * A JRE version other than {other}.
	 *
	 * <p>This constant returns {{@link Integer#MAX_VALUE}} for its
	 * {{@linkplain #version() version}}. To retrieve the actual version number,
	 * use {{@link #currentVersionNumber()}}.
	 */
	OTHER(Integer.MAX_VALUE);

	static final int UNDEFINED_VERSION = -1;

	static final int MINIMUM_VERSION = {minimum};

	private static final int CURRENT_VERSION = Runtime.version().feature();

	private final int version;

	JRE(int version) {{
		this.version = version;
	}}

	/**
	 * Get the version of <em>this</em> {{@code JRE}}.
	 *
	 * <p>If this {{@code JRE}} is {{@link #UNDEFINED}}, this method returns
	 * {{@code -1}}. If this {{@code JRE}} is {{@link #OTHER}}, this method returns
	 * {{@link Integer#MAX_VALUE}}.
	 *
	 * @return the version of this {{@code JRE}}
	 * @since 5.12
	 * @see Runtime.Version#feature()
	 * @see #currentVersionNumber()
	 */
	@API(status = MAINTAINED, since = "5.13.3")
	public int version() {{
		return this.version;
	}}

	/**
	 * {{@return {{@code true}} if <em>this</em> {{@code JRE}} is known to be the
	 * Java Runtime Environment version for the currently executing JVM or if
	 * the version is {{@link #OTHER}}}}
	 *
	 * @see #currentJre()
	 * @see #currentVersionNumber()
	 */
	public boolean isCurrentVersion() {{
		return this == currentJre();
	}}

	/**
	 * {{@return the {{@link JRE}} for the currently executing JVM, potentially
	 * {{@link #OTHER}}}}
	 *
	 * @since 5.7
	 * @see #currentVersionNumber()
	 * @deprecated in favor of {{@link #currentJre()}}
	 */
	@API(status = DEPRECATED, since = "5.12")
	@Deprecated(since = "5.12")
	public static JRE currentVersion() {{
		return currentJre();
	}}

	/**
	 * {{@return the {{@link JRE}} for the currently executing JVM, potentially
	 * {{@link #OTHER}}}}
	 *
	 * @since 5.12
	 * @see #currentVersionNumber()
	 */
	@API(status = STABLE, since = "5.12")
	public static JRE currentJre() {{
		return switch (CURRENT_VERSION) {{
{cases}
			default -> OTHER;
		}};
	}}

	/**
	 * {{@return the version number for the currently executing JVM, or {{@code -1}}
	 * if the current JVM version could not be determined}}
	 *
	 * @since 5.12
	 * @see Runtime.Version#feature()
	 * @see #currentJre()
	 */
	@API(status = MAINTAINED, since = "5.13.3")
	public static int currentVersionNumber() {{
		return CURRENT_VERSION;
	}}

	/**
	 * Determine if the supplied version number is considered to be the current
	 * JRE version.
	 *
	 * <p>Returns {{@code true}} if either of the following is {{@code true}}.
	 *
	 * <ul>
	 * <li>The supplied version number is known to be the Java Runtime Environment
	 * version for the currently executing JVM.</li>
	 * <li>The supplied version number is {{@link Integer#MAX_VALUE}} and the current
	 * {{@code JRE}} is {{@link JRE#OTHER OTHER}}.</li>
	 * </ul>
	 *
	 * @return {{@code true}} if the supplied version number is considered to be
	 * the current JRE version
	 * @since 5.12
	 * @see Runtime.Version#feature()
	 * @see #isCurrentVersion()
	 * @see #currentJre()
	 */
	@API(status = MAINTAINED, since = "5.13.3")
	public static boolean isCurrentVersion(int version) {{
		return (version == CURRENT_VERSION) || (version == JRE.currentJre().version);
	}}

	static boolean isCurrentVersionWithinRange(int min, int max) {{
		return CURRENT_VERSION >= min && CURRENT_VERSION <= max;
	}}

}}
""".format(
        header=header,
        see=see,
        constants=constants,
        other=other_links,
        minimum=minimum,
        cases=cases,
    )


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    min_runtime = 17
    jres = parse_jres(
        (root / "gradle/base/code-generator-model/src/main/resources/jre.yaml").read_text(encoding="utf-8")
    )
    versions = [jre["version"] for jre in jres]
    if versions != list(range(8, 27)):
        raise SystemExit("jre.yaml versions are %s" % versions)
    header = (root / "gradle/config/spotless/eclipse-public-license-2.0.java").read_text(encoding="utf-8").strip() + "\n"
    text = render(jres, header, min_runtime)
    for version in versions:
        token = "JAVA_%d(%d)" % (version, version)
        if token not in text:
            raise SystemExit("missing " + token)
        case = "case %d -> JAVA_%d;" % (version, version)
        if case not in text:
            raise SystemExit("missing " + case)
    if "JAVA_16" not in text or '@Deprecated(since = "6.0", forRemoval = true)' not in text:
        raise SystemExit("missing deprecation for JREs below 17")
    if "MINIMUM_VERSION = 8" not in text:
        raise SystemExit("MINIMUM_VERSION drifted")
    if "case 27 ->" in text:
        raise SystemExit("template does not list Java 27")
    # Java 17 is supported, so its constant is not the deprecated form.
    java17 = text.split("JAVA_17(17)", 1)[0].rsplit("/**", 1)[1]
    if "@Deprecated" in java17:
        raise SystemExit("JAVA_17 must not be deprecated")
    java16 = text.split("JAVA_16(16)", 1)[0].rsplit("/**", 1)[1]
    if "@Deprecated" not in java16:
        raise SystemExit("JAVA_16 must be deprecated")
    dest = root / "junit-jupiter-api/src/main/java/org/junit/jupiter/api/condition/JRE.java"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    print("wrote %s (%d jres)" % (dest, len(jres)))


if __name__ == "__main__":
    main()
