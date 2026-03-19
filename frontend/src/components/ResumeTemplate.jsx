import { Document, Page, Text, View, StyleSheet } from "@react-pdf/renderer";

const styles = StyleSheet.create({
  page: { padding: 40, fontSize: 10, fontFamily: "Helvetica", color: "#222" },
  name: { fontSize: 18, fontFamily: "Helvetica-Bold", marginBottom: 2 },
  contactRow: { flexDirection: "row", gap: 12, marginBottom: 12, color: "#555" },
  sectionTitle: {
    fontSize: 11,
    fontFamily: "Helvetica-Bold",
    borderBottomWidth: 1,
    borderBottomColor: "#ccc",
    paddingBottom: 2,
    marginTop: 10,
    marginBottom: 6,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  summary: { marginBottom: 4, lineHeight: 1.4 },
  entryHeader: { flexDirection: "row", justifyContent: "space-between", marginBottom: 2 },
  bold: { fontFamily: "Helvetica-Bold" },
  italic: { fontFamily: "Helvetica-Oblique", color: "#555" },
  bullet: { flexDirection: "row", marginBottom: 2, paddingLeft: 8 },
  bulletDot: { width: 8 },
  bulletText: { flex: 1, lineHeight: 1.4 },
  skillsText: { lineHeight: 1.5 },
});

export default function ResumeTemplate({ data }) {
  const pi = data.personal_info || {};
  const contactParts = [pi.email, pi.phone, pi.linkedin].filter(Boolean);

  return (
    <Document>
      <Page size="LETTER" style={styles.page}>
        {/* Name */}
        {pi.name && <Text style={styles.name}>{pi.name}</Text>}

        {/* Contact info */}
        {contactParts.length > 0 && (
          <View style={styles.contactRow}>
            {contactParts.map((c, i) => (
              <Text key={i}>{c}</Text>
            ))}
          </View>
        )}

        {/* Summary */}
        {data.summary && (
          <>
            <Text style={styles.sectionTitle}>Summary</Text>
            <Text style={styles.summary}>{data.summary}</Text>
          </>
        )}

        {/* Experience */}
        {data.experience?.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>Experience</Text>
            {data.experience.map((exp, i) => (
              <View key={i} style={{ marginBottom: 8 }}>
                <View style={styles.entryHeader}>
                  <Text>
                    <Text style={styles.bold}>{exp.title}</Text>
                    {exp.company ? `, ${exp.company}` : ""}
                  </Text>
                  <Text style={styles.italic}>
                    {[exp.start_date, exp.end_date].filter(Boolean).join(" - ")}
                  </Text>
                </View>
                {(exp.bullets || []).map((b, j) => (
                  <View key={j} style={styles.bullet}>
                    <Text style={styles.bulletDot}>-</Text>
                    <Text style={styles.bulletText}>{b}</Text>
                  </View>
                ))}
              </View>
            ))}
          </>
        )}

        {/* Education */}
        {data.education?.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>Education</Text>
            {data.education.map((edu, i) => (
              <View key={i} style={{ marginBottom: 6 }}>
                <View style={styles.entryHeader}>
                  <Text>
                    <Text style={styles.bold}>{edu.institution}</Text>
                    {edu.degree ? ` — ${edu.degree}` : ""}
                    {edu.field ? ` in ${edu.field}` : ""}
                  </Text>
                  <Text style={styles.italic}>
                    {[edu.start_date, edu.end_date].filter(Boolean).join(" - ")}
                  </Text>
                </View>
                {edu.gpa && <Text>GPA: {edu.gpa}</Text>}
              </View>
            ))}
          </>
        )}

        {/* Skills */}
        {data.skills?.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>Skills</Text>
            <Text style={styles.skillsText}>{data.skills.join(", ")}</Text>
          </>
        )}
      </Page>
    </Document>
  );
}
