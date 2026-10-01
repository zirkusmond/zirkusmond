import { createFileRoute } from "@tanstack/react-router";

import PageContainer from "#/components/zirkusmond/general/PageContainer.tsx";

interface DsgvoSection {
  heading: string;
  paragraphs: string[];
  list?: string[];
  links?: { text: string; href: string }[];
}

const SECTIONS: DsgvoSection[] = [
  {
    heading:
      "1. Erfassung allgemeiner Informationen beim Besuch unserer Website",
    paragraphs: [
      "Wenn Sie auf unsere Website zugreifen, d.h., wenn Sie sich nicht registrieren oder anderweitig Informationen übermitteln, werden automatisch Informationen allgemeiner Natur erfasst. Diese Informationen beinhalten etwa die Art des Webbrowsers, das verwendete Betriebssystem, den Domainnamen Ihres Internet-Service-Providers, Ihre IP-Adresse und Ähnliches.",
      "Diese Informationen dienen folgenden Zwecken:",
    ],
    list: [
      "Sicherstellung eines problemlosen Verbindungsaufbaus",
      "Sicherstellung einer reibungslosen Nutzung unserer Website",
      "Auswertung der Systemsicherheit und -stabilität",
      "Weitere administrative Zwecke",
    ],
  },
  {
    heading: "1.1 Rechtsgrundlage",
    paragraphs: [
      "Verarbeitung erfolgt gemäß Art. 6 Abs. 1 lit. f DSGVO auf Basis unseres berechtigten Interesses an der Verbesserung der Stabilität und Funktionalität unserer Website.",
    ],
  },
  {
    heading: "1.2 Empfänger",
    paragraphs: [
      "Empfänger der Daten sind ggf. technische Dienstleister, die für den Betrieb und die Wartung unserer Webseite als Auftragsverarbeiter tätig werden.",
    ],
  },
  {
    heading: "1.3 Speicherdauer",
    paragraphs: [
      "Die Daten werden gelöscht, sobald diese für den Zweck der Erhebung nicht mehr erforderlich sind. Dies ist für die Daten, die der Bereitstellung der Webseite dienen, grundsätzlich der Fall, wenn die jeweilige Sitzung beendet ist.",
    ],
  },
  {
    heading: "1.4 Bereitstellung vorgeschrieben oder erforderlich",
    paragraphs: [
      "Die Bereitstellung der vorgenannten personenbezogenen Daten ist weder gesetzlich noch vertraglich vorgeschrieben. Ohne die IP-Adresse ist jedoch der Dienst und die Funktionsfähigkeit unserer Website nicht gewährleistet. Zudem können einzelne Dienste und Services nicht verfügbar oder eingeschränkt sein. Aus diesem Grund ist ein Widerspruch ausgeschlossen.",
    ],
  },
  {
    heading: "2. Cookies",
    paragraphs: [
      "Unsere Website verwendet Cookies, um die Nutzererfahrung zu verbessern. Cookies sind kleine Textdateien, die auf Ihrem Gerät gespeichert werden und uns helfen, Ihre Nutzung der Website besser zu verstehen.",
      "Sie können die Verwendung von Cookies jederzeit über die Einstellungen Ihres Browsers deaktivieren.",
    ],
  },
  {
    heading: "2.1 Fehlerüberwachung und Performance-Tracking (Sentry)",
    paragraphs: [
      "Wir verwenden Sentry, einen Dienst zur Fehlerüberwachung und Performance-Analyse, um die Stabilität und Funktionalität unserer Website zu verbessern. Sentry erfasst technische Informationen über Fehler, Browsertyp, Betriebssystem und Performance-Metriken.",
      "Die Verarbeitung erfolgt nur mit Ihrer ausdrücklichen Einwilligung gemäß Art. 6 Abs. 1 lit. a DSGVO. Sie können Ihre Einwilligung jederzeit über unser Cookie-Banner widerrufen.",
    ],
  },
  {
    heading: "2.2 Rechtsgrundlage",
    paragraphs: [
      "Die Verarbeitung erfolgt auf Basis Ihrer Einwilligung (Art. 6 Abs. 1 lit. a DSGVO).",
    ],
  },
  {
    heading: "2.3 Empfänger",
    paragraphs: [
      "Empfänger der Daten ist Functional Software, Inc. (Sentry) als Auftragsverarbeiter.",
    ],
  },
  {
    heading: "2.4 Speicherdauer",
    paragraphs: [
      "Sentry speichert Fehlerdaten für 90 Tage. Performance-Daten werden nach 30 Tagen gelöscht.",
    ],
  },
  {
    heading: "2.5 Drittlandtransfer",
    paragraphs: [
      "Sentry verarbeitet Daten in den USA und der EU. Die Datenübertragung erfolgt auf Grundlage von Standardvertragsklauseln der EU-Kommission.",
    ],
  },
  {
    heading: "2.6 Bereitstellung vorgeschrieben oder erforderlich",
    paragraphs: [
      "Die Bereitstellung Ihrer Daten erfolgt freiwillig auf Basis Ihrer Einwilligung. Ohne Sentry können wir technische Probleme möglicherweise nicht so schnell identifizieren und beheben.",
    ],
  },
  {
    heading: "3. Registrierung auf unserer Website",
    paragraphs: [
      "Bei der Registrierung für personalisierte Leistungen erheben wir personenbezogene Daten wie Name, Adresse und E-Mail-Adresse. Registrierte Nutzer haben Zugriff auf exklusive Inhalte und Funktionen.",
    ],
  },
  {
    heading: "3.1 Rechtsgrundlage",
    paragraphs: [
      "Die Verarbeitung der bei der Registrierung angegebenen Daten basiert auf der Einwilligung des Nutzers gemäß Artikel 6 Absatz 1 lit. a der Datenschutz-Grundverordnung (DSGVO).",
    ],
  },
  {
    heading: "3.2 Empfänger",
    paragraphs: [
      "Mögliche Empfänger der Daten sind externe technische Dienstleister, die als Auftragsverarbeiter für den Betrieb und die Wartung unserer Website tätig sind.",
    ],
  },
  {
    heading: "3.3 Speicherdauer",
    paragraphs: [
      "Die Daten werden nur solange verarbeitet, wie die entsprechende Einwilligung vorliegt. Nach Ablauf der Einwilligung werden die Daten gelöscht, sofern keine gesetzlichen Aufbewahrungspflichten bestehen. Bei Fragen oder Anliegen in diesem Zusammenhang nutzen Sie bitte die Kontaktdaten, die am Ende dieser Datenschutzerklärung angegeben sind.",
    ],
  },
  {
    heading: "3.4 Bereitstellung vorgeschrieben oder erforderlich",
    paragraphs: [
      "Die Bereitstellung Ihrer personenbezogenen Daten erfolgt freiwillig und basiert ausschließlich auf Ihrer Einwilligung. Ohne die Bereitstellung Ihrer personenbezogenen Daten können wir Ihnen keinen Zugang zu unseren angebotenen Inhalten und Leistungen gewähren.",
    ],
  },
  {
    heading: "4. Erbringung kostenpflichtiger Leistungen",
    paragraphs: [
      "Zur Erbringung kostenpflichtiger Leistungen werden von uns zusätzliche Daten erfragt, wie z.B. Zahlungsangaben, um Ihre Bestellung ausführen zu können.",
    ],
  },
  {
    heading: "4.1 Rechtsgrundlage",
    paragraphs: [
      "Gemäß Artikel 6 Absatz 1 lit. b der Datenschutz-Grundverordnung (DSGVO) erfolgt die Verarbeitung der erforderlichen Daten zur Erfüllung des Vertragszwecks.",
    ],
  },
  {
    heading: "4.2 Empfänger",
    paragraphs: ["Empfänger der Daten sind ggf. Auftragsverarbeiter."],
  },
  {
    heading: "4.3 Speicherdauer",
    paragraphs: [
      "Wir speichern diese Daten in unseren Systemen bis die gesetzlichen Aufbewahrungsfristen abgelaufen sind. Diese betragen grundsätzlich 6 oder 10 Jahre aus Gründen der ordnungsmäßigen Buchführung und steuerrechtlichen Anforderungen.",
    ],
  },
  {
    heading: "4.4 Bereitstellung vorgeschrieben oder erforderlich",
    paragraphs: [
      "Die Bereitstellung Ihrer personenbezogenen Daten erfolgt freiwillig. Bitte beachten Sie jedoch, dass ohne die Bereitstellung Ihrer personenbezogenen Daten kein Zugang zu unseren angebotenen Inhalten und Leistungen möglich ist.",
    ],
  },
  {
    heading: "5. Kontaktformular",
    paragraphs: [
      "Die von Ihnen eingegebenen Daten werden zum Zweck der individuellen Kommunikation mit Ihnen gespeichert. Hierfür ist die Angabe einer validen E-Mail-Adresse sowie Ihres Namens erforderlich. Diese dient der Zuordnung der Anfrage und der anschließenden Beantwortung derselben. Die Angabe weiterer Daten ist optional.",
    ],
  },
  {
    heading: "5.1 Rechtsgrundlage",
    paragraphs: [
      "Die Verarbeitung der bei der Registrierung angegebenen Daten erfolgt mit Ihrer Einwilligung gemäß Artikel 6 Absatz 1 lit. a der Datenschutz-Grundverordnung (DSGVO) als rechtliche Grundlage.",
    ],
  },
  {
    heading: "5.2 Empfänger",
    paragraphs: [
      "Gegebenenfalls werden die Daten an Auftragsverarbeiter weitergegeben.",
    ],
  },
  {
    heading: "5.3 Speicherdauer",
    paragraphs: [
      "Daten werden spätestens 6 Monate nach Bearbeitung der Anfrage gelöscht. Sofern es zu einem Vertragsverhältnis kommt, unterliegen wir den gesetzlichen Aufbewahrungsfristen nach HGB und löschen Ihre Daten nach Ablauf dieser Fristen.",
    ],
  },
  {
    heading: "5.4 Bereitstellung vorgeschrieben oder erforderlich",
    paragraphs: [
      "Die Bereitstellung Ihrer personenbezogenen Daten erfolgt freiwillig. Bitte beachten Sie jedoch, dass wir Ihre Anfrage nur bearbeiten können, wenn Sie uns Ihren Namen, Ihre E-Mail-Adresse und den Grund Ihrer Anfrage mitteilen.",
    ],
  },
  {
    heading: "6. Verwendung von Google Analytics",
    paragraphs: [
      "Diese Website benutzt Google Analytics, einen Webanalysedienst der Google LLC. Google Analytics verwendet Cookies, um eine Analyse der Nutzung der Webseite zu ermöglichen.",
    ],
  },
  {
    heading: "6.1 Rechtsgrundlage",
    paragraphs: [
      "Die Verarbeitung Ihrer Daten erfolgt nur mit Ihrer ausdrücklichen Einwilligung gemäß Artikel 6 Absatz 1 Buchstabe a der DSGVO.",
    ],
  },
  {
    heading: "6.2 Empfänger",
    paragraphs: ["Empfänger der Daten ist Google als Auftragsverarbeiter."],
  },
  {
    heading: "6.3 Speicherdauer",
    paragraphs: [
      "Die Löschung der Daten erfolgt, sobald diese für unsere Aufzeichnungszwecke nicht mehr erforderlich sind.",
    ],
  },
  {
    heading: "6.4 Drittlandtransfer",
    paragraphs: [
      "Google verarbeitet Ihre Daten in den USA und hat sich dem EU_US Privacy Shield unterworfen.",
    ],
  },
  {
    heading: "6.5 Bereitstellung vorgeschrieben oder erforderlich",
    paragraphs: [
      "Die Bereitstellung Ihrer personenbezogenen Daten erfolgt freiwillig und ausschließlich auf Basis Ihrer Einwilligung.",
    ],
  },
  {
    heading: "7. Widerruf der Einwilligung",
    paragraphs: [
      "Zusätzlich oder als Alternative können Sie das Tracking durch Google Analytics auf unseren Seiten unterbinden.",
    ],
  },
  {
    heading: "8. Profiling",
    paragraphs: [
      "Mit Hilfe von Google Analytics kann das Verhalten der Besucher der Webseite bewertet und Interessen analysiert werden.",
    ],
  },
  {
    heading: "9. Verwendung von Google Webfonts",
    paragraphs: [
      "Um unsere Inhalte korrekt und ansprechend darzustellen, verwenden wir Google Web Fonts.",
    ],
  },
  {
    heading: "9.1 Rechtsgrundlage",
    paragraphs: [
      "Rechtsgrundlage für die Einbindung von Google Webfonts und dem damit verbundenen Datentransfer zu Google ist Ihre Einwilligung (Art. 6 Abs. 1 lit. a DSGVO).",
    ],
  },
  {
    heading: "9.2 Empfänger",
    paragraphs: [
      "Der Aufruf von Scriptbibliotheken oder Schriftbibliotheken löst automatisch eine Verbindung zum Betreiber der Bibliothek aus. Dabei ist es theoretisch möglich, dass der Betreiber in diesem Fall Google Daten erhebt.",
    ],
  },
  {
    heading: "9.3 Speicherdauer",
    paragraphs: [
      "Wir erheben keine personenbezogenen Daten durch die Einbindung von Google Webfonts.",
    ],
    links: [
      {
        text: "Weitere Informationen zu Google Web Fonts",
        href: "https://developers.google.com/fonts/faq",
      },
      {
        text: "Datenschutzerklärung von Google",
        href: "https://www.google.com/policies/privacy/",
      },
    ],
  },
  {
    heading: "9.4 Drittlandtransfer",
    paragraphs: [
      "Google verarbeitet Ihre Daten in den USA und hat sich den Bestimmungen des EU-US-Datenschutzschilds unterworfen.",
    ],
    links: [
      {
        text: "Mehr dazu",
        href: "https://www.privacyshield.gov/EU-US-Framework",
      },
    ],
  },
  {
    heading: "9.5 Bereitstellung vorgeschrieben oder erforderlich",
    paragraphs: [
      "Die Bereitstellung der personenbezogenen Daten ist weder gesetzlich noch vertraglich vorgeschrieben. Ohne Webfonts kann jedoch die korrekte Darstellung von Inhalten eingeschränkt sein.",
    ],
  },
  {
    heading: "9.6 Widerruf der Einwilligung",
    paragraphs: [
      "Zur Darstellung der Inhalte wird regelmäßig die Programmiersprache JavaScript verwendet. Sie können der Datenverarbeitung widersprechen, indem Sie JavaScript in Ihrem Browser deaktivieren oder einen JavaScript-Blocker installieren. Beachten Sie, dass dadurch Funktionseinschränkungen auftreten können.",
    ],
  },
  {
    heading: "10. Verwendung von Google Maps",
    paragraphs: [
      "Unsere Webseite nutzt Google Maps, um interaktive Karten bereitzustellen.",
    ],
  },
  {
    heading: "10.1 Rechtsgrundlage",
    paragraphs: [
      "Rechtsgrundlage für die Einbindung von Google Maps und dem damit verbundenen Datentransfer zu Google ist Ihre Einwilligung (Art. 6 Abs. 1 lit. a DSGVO).",
    ],
  },
  {
    heading: "10.2 Empfänger",
    paragraphs: [
      "Durch den Besuch der Webseite erhält Google Informationen, dass Sie die entsprechende Unterseite unserer Webseite aufgerufen haben. Dies erfolgt unabhängig davon, ob Google ein Nutzerkonto bereitstellt oder nicht. Falls Sie eingeloggt sind, wird Ihre Aktivität direkt Ihrem Konto zugeordnet.",
      "Wenn Sie dies nicht wünschen, loggen Sie sich bitte vor Aktivierung von Google Maps bei Google aus. Google speichert Ihre Daten als Nutzungsprofile für Werbung, Marktforschung und bedarfsgerechte Webseiten-Gestaltung. Ihnen steht ein Widerspruchsrecht gegen die Bildung dieser Nutzerprofile zu, das Sie bei Google geltend machen müssen.",
    ],
  },
  {
    heading: "10.3 Speicherdauer",
    paragraphs: [
      "Wir erheben keine personenbezogenen Daten durch die Einbindung von Google Maps.",
    ],
  },
  {
    heading: "10.4 Drittlandtransfer",
    paragraphs: [
      "Google verarbeitet Ihre Daten in den USA und hat sich dem EU_US Privacy Shield unterworfen.",
    ],
    links: [
      {
        text: "Mehr dazu",
        href: "https://www.privacyshield.gov/EU-US-Framework",
      },
    ],
  },
  {
    heading: "10.5 Widerruf der Einwilligung",
    paragraphs: [
      "Falls Sie nicht möchten, dass Google über unseren Internetauftritt Daten über Sie erhebt oder verarbeitet, können Sie in den Browsereinstellungen JavaScript deaktivieren. Beachten Sie, dass dadurch Google Maps möglicherweise nicht mehr nutzbar ist.",
    ],
  },
  {
    heading: "10.6 Bereitstellung vorgeschrieben oder erforderlich",
    paragraphs: [
      "Die Bereitstellung Ihrer personenbezogenen Daten erfolgt freiwillig auf Basis Ihrer Einwilligung. Bei Verweigerung kann es zu Funktionseinschränkungen kommen.",
    ],
  },
  {
    heading: "11. Eingebettete YouTube-Videos",
    paragraphs: [
      "Auf einigen unserer Webseiten betten wir YouTube-Videos ein.",
    ],
  },
  {
    heading: "11.1 Rechtsgrundlage",
    paragraphs: [
      "Rechtsgrundlage für die Einbindung von YouTube und dem damit verbundenen Datentransfer zu Google ist Ihre Einwilligung (Art. 6 Abs. 1 lit. a DSGVO).",
    ],
  },
  {
    heading: "11.2 Empfänger",
    paragraphs: [
      "Der Aufruf von YouTube löst automatisch eine Verbindung zu Google aus.",
    ],
  },
  {
    heading: "11.3 Speicherdauer und Widerruf der Einwilligung",
    paragraphs: [
      "Wer das Speichern von Cookies für das Google-Ad-Programm deaktiviert hat, wird auch beim Anschauen von YouTube-Videos mit keinen solchen Cookies rechnen müssen. YouTube legt aber auch in anderen Cookies nicht-personenbezogene Nutzungsinformationen ab. Möchten Sie dies verhindern, so müssen Sie das Speichern von Cookies im Browser blockieren.",
    ],
    links: [
      {
        text: "Datenschutzerklärung von YouTube",
        href: "https://www.google.de/intl/de/policies/privacy/",
      },
    ],
  },
  {
    heading: "11.4 Drittlandtransfer",
    paragraphs: [
      "In den USA verarbeitet Google Ihre Daten und hat sich den Bestimmungen des EU-US-Datenschutzschilds unterworfen.",
    ],
    links: [
      {
        text: "Mehr dazu",
        href: "https://www.privacyshield.gov/EU-US-Framework",
      },
    ],
  },
  {
    heading: "11.5 Bereitstellung vorgeschrieben oder erforderlich",
    paragraphs: [
      "Die Bereitstellung Ihrer personenbezogenen Daten erfolgt freiwillig und basiert allein auf Ihrer Einwilligung. Bitte beachten Sie, dass eine Einschränkung des Zugriffs zu Funktionseinschränkungen auf der Website führen kann.",
    ],
  },
  {
    heading: "12. Google AdWords",
    paragraphs: [
      "Unsere Webseite nutzt Google Conversion-Tracking zur Erfolgsmessung von Anzeigen.",
    ],
  },
  {
    heading: "12.1 Rechtsgrundlage",
    paragraphs: [
      "Rechtsgrundlage für die Einbindung von Google AdWords und dem damit verbundenen Datentransfer zu Google ist Ihre Einwilligung (Art. 6 Abs. 1 lit. a DSGVO).",
    ],
  },
  {
    heading: "12.2 Empfänger",
    paragraphs: [
      "Bei jedem Besuch unserer Webseite werden personenbezogene Daten, einschließlich Ihrer IP-Adresse, an Google in die USA übertragen. Diese personenbezogenen Daten werden durch Google gespeichert und unter Umständen an Dritte weitergegeben.",
    ],
  },
  {
    heading: "12.3 Speicherdauer",
    paragraphs: [
      "Diese Cookies verlieren nach 30 Tagen ihre Gültigkeit und dienen nicht der persönlichen Identifizierung.",
    ],
  },
  {
    heading: "12.4 Drittlandtransfer",
    paragraphs: [
      "Google verarbeitet Ihre Daten in den USA und hat sich dem EU_US Privacy Shield unterworfen.",
    ],
  },
  {
    heading: "12.5 Widerruf der Einwilligung",
    paragraphs: [
      "Sie können das Setzen eines Cookies ablehnen, indem Sie die entsprechenden Browsereinstellungen vornehmen.",
    ],
  },
  {
    heading: "12.6 Bereitstellung vorgeschrieben oder erforderlich",
    paragraphs: [
      "Die Entscheidung, Ihre personenbezogenen Daten bereitzustellen, liegt ganz bei Ihnen. Eine Einschränkung kann jedoch zu Beeinträchtigungen der Website-Funktionen führen.",
    ],
  },
  {
    heading: "13. SSL-Verschlüsselung",
    paragraphs: [
      "Zum Schutz Ihrer Daten nutzen wir moderne Verschlüsselungsverfahren (SSL) über HTTPS.",
    ],
  },
  {
    heading: "14. Änderung unserer Datenschutzbestimmungen",
    paragraphs: [
      "Wir behalten uns vor, diese Datenschutzerklärung anzupassen, um sie aktuellen rechtlichen Anforderungen anzupassen.",
    ],
  },
  {
    heading: "15. Fragen an den Datenschutzbeauftragten",
    paragraphs: [
      "Wenn Sie Fragen zum Datenschutz haben, schreiben Sie uns bitte eine E-Mail oder wenden Sie sich direkt an die verantwortliche Person:",
    ],
    links: [
      {
        text: "mail@zirkusmond.de",
        href: "mailto:mail@zirkusmond.de",
      },
    ],
  },
];

const RouteComponent = () => {
  return (
    <PageContainer>
      <h1 className="mb-8 text-white">IHRE BETROFFENENRECHTE</h1>
      <div className="flex flex-col gap-8">
        {SECTIONS.map((section) => (
          <section key={section.heading}>
            <h2 className="mb-2 text-primary">{section.heading}</h2>
            {section.paragraphs.map((paragraph, i) => (
              <p key={i} className="my-2">
                {paragraph}
              </p>
            ))}
            {section.list && (
              <ul className="list-disc pl-5">
                {section.list.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
            {section.links && (
              <p className="my-2 flex flex-wrap gap-x-2">
                {section.links.map((link) => (
                  <a
                    key={link.href}
                    className="underline hover:text-white"
                    href={link.href}
                  >
                    {link.text}
                  </a>
                ))}
              </p>
            )}
          </section>
        ))}
      </div>
    </PageContainer>
  );
};

export const Route = createFileRoute("/datenschutz")({
  head: () => ({
    meta: [{ title: "Zirkus Mond - Datenschutz" }],
  }),
  component: RouteComponent,
});
