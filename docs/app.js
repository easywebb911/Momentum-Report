/* Momentum-Report — Bedienung der Seite. Kein Framework.
 *
 * Vier Dinge:
 *   1. Menue und Textgroesse (--app-fs auf <html>; alles ist rem-basiert,
 *      also skaliert die gesamte Oberflaeche mit)
 *   2. "Neu laden" — holt dieselbe Seite frisch und tauscht den Inhalt aus,
 *      ohne die Seite neu zu oeffnen
 *   3. "Neu berechnen" — stoesst den Momentum-Lauf per workflow_dispatch an
 *      und verfolgt ihn, bis er fertig ist ODER fehlschlaegt
 *   4. Zugriffs-Token: Dialog, Ablage auf dem Geraet, "Sperren"
 *
 * ZUM TOKEN, ausdruecklich:
 *   - Er geht NUR als Authorization-Kopfzeile an api.github.com.
 *   - Er steht NIE in einer Adresszeile (kein Query-Parameter) und NIE in
 *     einer Protokollausgabe -- es gibt in dieser Datei keine einzige
 *     Ausgabe, die ihn beruehrt.
 *   - Er liegt auf dem Geraet in IndexedDB, mit Ablaufdatum. Wer das Geraet
 *     entsperrt hat, kann ihn benutzen; das ist die Grenze dieses Verfahrens
 *     und steht so auch im Dialog.
 *
 * PRUEFBARKEIT: Alles Aeussere haengt an MR.deps (netz, jetzt, Abstaende).
 * Tests ersetzen diese Felder und fahren die Ablaeufe damit durch, ohne
 * einen einzigen echten Netzzugriff.
 */
(function () {
  "use strict";

  var KEY = "momentum-report:fs";
  var DB_NAME = "momentum-report";
  var STORE = "sitzung";
  var TOKEN_SCHLUESSEL = "pat";
  var SITZUNG_MS = 28 * 24 * 60 * 60 * 1000; // 28 Tage
  var API = "https://api.github.com";

  var root = document.documentElement;
  var koerper = document.body;
  var btn = document.getElementById("menu-btn");
  var overlay = document.getElementById("overlay");

  // Aus config.py in die Seite gerendert -- eine Wahrheit, kein zweiter Ort.
  var REPO = koerper.getAttribute("data-repo") || "";
  var WORKFLOW = koerper.getAttribute("data-workflow") || "";

  var deps = {
    netz: function (url, opt) { return fetch(url, opt); },
    jetzt: function () { return Date.now(); },
    pollAbstandMs: 5000,
    zeitlimitMs: 10 * 60 * 1000
  };

  // ---------------------------------------------------------- Textgroesse

  function setFontSize(px, persist) {
    root.style.setProperty("--app-fs", px + "px");
    if (persist) {
      try { localStorage.setItem(KEY, String(px)); } catch (err) { /* Privatmodus */ }
    }
    var buttons = document.querySelectorAll(".fs-btn");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute(
        "aria-pressed",
        buttons[i].getAttribute("data-fs") === String(px) ? "true" : "false"
      );
    }
  }

  var stored = null;
  try { stored = localStorage.getItem(KEY); } catch (err) { stored = null; }
  setFontSize(stored ? parseInt(stored, 10) : 16, false);

  // ---------------------------------------------------------------- Menue

  function openMenu() {
    overlay.hidden = false;
    btn.setAttribute("aria-expanded", "true");
  }
  function closeMenu() {
    if (!overlay || !btn) { return; }
    overlay.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  }

  if (btn && overlay) {
    btn.addEventListener("click", function () {
      if (overlay.hidden) { openMenu(); } else { closeMenu(); }
    });
    overlay.addEventListener("click", function (event) {
      if (event.target.hasAttribute("data-close")) { closeMenu(); }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !overlay.hidden) { closeMenu(); }
    });
  }

  document.addEventListener("click", function (event) {
    var target = event.target.closest ? event.target.closest(".fs-btn") : null;
    if (target) { setFontSize(parseInt(target.getAttribute("data-fs"), 10), true); }
  });

  // -------------------------------------------------------------- Ablage
  // IndexedDB, nicht localStorage: der Token gehoert nicht in denselben
  // Topf wie die Textgroessen-Einstellung, und ein Eintrag mit Ablaufdatum
  // laesst sich hier sauber als Objekt halten.

  function db() {
    return new Promise(function (ok, fehl) {
      var anfrage = indexedDB.open(DB_NAME, 1);
      anfrage.onupgradeneeded = function () {
        anfrage.result.createObjectStore(STORE);
      };
      anfrage.onsuccess = function () { ok(anfrage.result); };
      anfrage.onerror = function () { fehl(anfrage.error); };
    });
  }

  function mitStore(modus, arbeit) {
    return db().then(function (verbindung) {
      return new Promise(function (ok, fehl) {
        var vorgang = verbindung.transaction(STORE, modus);
        var anfrage = arbeit(vorgang.objectStore(STORE));
        anfrage.onsuccess = function () { ok(anfrage.result); };
        anfrage.onerror = function () { fehl(anfrage.error); };
        vorgang.oncomplete = function () { verbindung.close(); };
      });
    });
  }

  function sitzungSchreiben(token) {
    var eintrag = { token: token, gueltig_bis: deps.jetzt() + SITZUNG_MS };
    return mitStore("readwrite", function (s) {
      return s.put(eintrag, TOKEN_SCHLUESSEL);
    }).then(function () { return eintrag; });
  }

  /** Der Eintrag — oder null, wenn keiner da oder abgelaufen ist. */
  function sitzungLesen() {
    return mitStore("readonly", function (s) { return s.get(TOKEN_SCHLUESSEL); })
      .then(function (eintrag) {
        if (!eintrag || !eintrag.token) { return null; }
        if (!eintrag.gueltig_bis || eintrag.gueltig_bis <= deps.jetzt()) {
          // Abgelaufen: nicht bloss ignorieren, sondern wirklich wegraeumen.
          return sitzungLoeschen().then(function () { return null; });
        }
        return eintrag;
      })
      .catch(function () { return null; });
  }

  function sitzungLoeschen() {
    return mitStore("readwrite", function (s) {
      return s.delete(TOKEN_SCHLUESSEL);
    }).catch(function () { return null; });
  }

  // -------------------------------------------------------------- Banner

  var bar = document.getElementById("runbar");
  var barText = document.getElementById("runbar-text");
  var barLink = document.getElementById("runbar-link");
  var barClose = document.getElementById("runbar-close");

  function bannerZeigen(art, text, url) {
    if (!bar) { return; }
    bar.hidden = false;
    bar.className = "runbar runbar--" + art;
    barText.textContent = text;
    if (url) {
      barLink.href = url;
      barLink.hidden = false;
    } else {
      barLink.hidden = true;
      barLink.removeAttribute("href");
    }
  }

  if (barClose) {
    barClose.addEventListener("click", function () { bar.hidden = true; });
  }

  // ----------------------------------------------------------- Neu laden
  // Kein location.reload(): die Seite wird geholt und ihr Inhalt getauscht.
  // Der Cache-Brecher haengt am Zeitstempel -- sonst liefert der Browser-
  // bzw. PWA-Cache genau die alte Fassung zurueck, und der Knopf waere eine
  // Luege.

  function neuLaden() {
    var ziel = location.pathname.split("?")[0] + "?t=" + deps.jetzt();
    return deps.netz(ziel, { cache: "no-store" })
      .then(function (antwort) {
        if (!antwort.ok) { throw new Error("HTTP " + antwort.status); }
        return antwort.text();
      })
      .then(function (text) {
        var frisch = new DOMParser().parseFromString(text, "text/html");
        var altMain = document.querySelector("main");
        var neuMain = frisch.querySelector("main");
        if (!altMain || !neuMain) { throw new Error("Seite ohne Inhalt"); }
        altMain.replaceWith(neuMain);
        var altStand = document.querySelector(".stand");
        var neuStand = frisch.querySelector(".stand");
        if (altStand && neuStand) { altStand.textContent = neuStand.textContent; }
        return neuStand ? neuStand.textContent : "";
      });
  }

  // ------------------------------------------------------- Lauf anstossen

  function kopfzeilen(token) {
    return {
      "Authorization": "Bearer " + token,
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28"
    };
  }

  function amLimit(antwort) {
    // GitHub meldet das Limit als 403 mit x-ratelimit-remaining: 0.
    if (antwort.status !== 403 && antwort.status !== 429) { return false; }
    if (antwort.status === 429) { return true; }
    var rest = antwort.headers && antwort.headers.get
      ? antwort.headers.get("x-ratelimit-remaining")
      : null;
    return rest === "0";
  }

  /** Uebersetzt eine abgelehnte Antwort in eine ehrliche Meldung. */
  function ablehnung(antwort) {
    if (amLimit(antwort)) {
      return {
        text: "GitHub-API am Limit. Kein zweiter Versuch — Wiederholen macht " +
              "es nur schlimmer. Bitte spaeter noch einmal.",
        tokenWeg: false
      };
    }
    if (antwort.status === 401) {
      return {
        text: "Der Token wird abgelehnt (401). Er ist abgelaufen oder " +
              "widerrufen — bitte einen neuen anlegen.",
        tokenWeg: true
      };
    }
    if (antwort.status === 403) {
      return {
        text: "Der Token darf das nicht (403). Er braucht fuer dieses " +
              "Repository Actions: Read and write.",
        tokenWeg: false
      };
    }
    if (antwort.status === 404) {
      return {
        text: "Repository oder Workflow nicht gefunden (404). Meist heisst " +
              "das: der Token gilt nicht fuer dieses Repository.",
        tokenWeg: false
      };
    }
    return {
      text: "GitHub hat abgelehnt (HTTP " + antwort.status + ").",
      tokenWeg: false
    };
  }

  function laufUrl() { return "https://github.com/" + REPO + "/actions"; }

  function anstossen(token) {
    return deps.netz(
      API + "/repos/" + REPO + "/actions/workflows/" + WORKFLOW + "/dispatches",
      {
        method: "POST",
        headers: kopfzeilen(token),
        body: JSON.stringify({ ref: "main" })
      }
    );
  }

  /** Den Lauf finden, den WIR angestossen haben — alles Aeltere zaehlt nicht. */
  function laufSuchen(token, start) {
    var url = API + "/repos/" + REPO + "/actions/workflows/" + WORKFLOW +
      "/runs?branch=main&event=workflow_dispatch&per_page=5";
    return deps.netz(url, { headers: kopfzeilen(token) }).then(function (antwort) {
      if (!antwort.ok) { return { fehler: ablehnung(antwort) }; }
      return antwort.json().then(function (daten) {
        var laeufe = (daten && daten.workflow_runs) || [];
        for (var i = 0; i < laeufe.length; i++) {
          // 90 s Vorlauf: die Uhr des Geraets und die von GitHub gehen selten
          // genau gleich, und der Lauf wird eine Spur vor der Antwort angelegt.
          if (Date.parse(laeufe[i].created_at) >= start - 90000) {
            return { lauf: laeufe[i] };
          }
        }
        return {};
      });
    });
  }

  function sekunden(start) {
    return Math.max(0, Math.round((deps.jetzt() - start) / 1000));
  }

  /**
   * Verfolgt den Lauf bis zum Ende. Loest auf mit "fertig",
   * "fehlgeschlagen", "zeitlimit" oder "abgebrochen" — nie mit einem
   * ewigen Zaehler.
   */
  function verfolgen(token, start, letzter) {
    if (deps.jetzt() - start > deps.zeitlimitMs) {
      bannerZeigen(
        "fehler",
        "Lauf dauert ungewoehnlich lange (" + sekunden(start) + " s) — " +
        "Actions-Protokoll pruefen.",
        (letzter && letzter.html_url) || laufUrl()
      );
      return Promise.resolve("zeitlimit");
    }

    return laufSuchen(token, start).then(function (ergebnis) {
      if (ergebnis && ergebnis.fehler) {
        bannerZeigen("fehler", ergebnis.fehler.text, laufUrl());
        return "abgebrochen";
      }
      var lauf = (ergebnis && ergebnis.lauf) || letzter;

      if (lauf && lauf.status === "completed") {
        if (lauf.conclusion === "success") {
          return neuLaden().then(function () {
            bannerZeigen("fertig", "Neuberechnung fertig, Daten aktualisiert.", lauf.html_url);
            return "fertig";
          }).catch(function (err) {
            bannerZeigen(
              "fehler",
              "Lauf fertig, aber die neuen Daten liessen sich nicht holen: " +
              err.message,
              lauf.html_url
            );
            return "fertig";
          });
        }
        // DER EHRLICHE PFAD: rot ist rot. Kein Weiterzaehlen, keine
        // Beschoenigung — mit Verweis auf das Protokoll, das den Grund nennt.
        // Genau hier landet der Lauf heute, solange das DE-Universum ein
        // Platzhalter ist: er verweigert zu Recht, und das muss man sehen.
        bannerZeigen(
          "fehler",
          "Der Lauf ist fehlgeschlagen (" + (lauf.conclusion || "ohne Ergebnis") +
          "). Der Grund steht im Actions-Protokoll.",
          lauf.html_url
        );
        return "fehlgeschlagen";
      }

      bannerZeigen(
        "laeuft",
        "Neuberechnung laeuft… (" + sekunden(start) + " s)",
        lauf && lauf.html_url
      );
      return new Promise(function (ok) {
        setTimeout(ok, deps.pollAbstandMs);
      }).then(function () { return verfolgen(token, start, lauf); });
    }).catch(function (err) {
      bannerZeigen("fehler", "Verbindung zu GitHub abgebrochen: " + err.message, laufUrl());
      return "abgebrochen";
    });
  }

  function laufStarten(token) {
    var start = deps.jetzt();
    bannerZeigen("laeuft", "Lauf wird angestossen …", null);
    return anstossen(token).then(function (antwort) {
      if (antwort.status === 204) { return verfolgen(token, start, null); }
      var grund = ablehnung(antwort);
      bannerZeigen("fehler", grund.text, laufUrl());
      if (grund.tokenWeg) {
        return sitzungLoeschen().then(function () {
          return sitzungAnzeigen();
        }).then(function () {
          dialogOeffnen(grund.text);
          return "token-abgelehnt";
        });
      }
      return "abgelehnt";
    }).catch(function (err) {
      bannerZeigen("fehler", "Der Lauf liess sich nicht anstossen: " + err.message, null);
      return "abgebrochen";
    });
  }

  // --------------------------------------------------------- Token-Dialog

  var tokOverlay = document.getElementById("tok-overlay");
  var tokInput = document.getElementById("tok-input");
  var tokError = document.getElementById("tok-error");
  var tokSave = document.getElementById("tok-save");

  function dialogOeffnen(meldung) {
    if (!tokOverlay) { return; }
    closeMenu();
    tokOverlay.hidden = false;
    if (meldung) {
      tokError.textContent = meldung;
      tokError.hidden = false;
    } else {
      tokError.hidden = true;
    }
    if (tokInput) { tokInput.value = ""; tokInput.focus(); }
  }

  function dialogSchliessen() {
    if (!tokOverlay) { return; }
    tokOverlay.hidden = true;
    // Der Token bleibt nicht im Eingabefeld stehen.
    if (tokInput) { tokInput.value = ""; }
  }

  if (tokOverlay) {
    tokOverlay.addEventListener("click", function (event) {
      if (event.target.hasAttribute("data-tok-close")) { dialogSchliessen(); }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !tokOverlay.hidden) { dialogSchliessen(); }
    });
  }

  if (tokSave) {
    tokSave.addEventListener("click", function () {
      var wert = (tokInput.value || "").trim();
      if (!wert) {
        tokError.textContent = "Bitte den Token einsetzen.";
        tokError.hidden = false;
        return;
      }
      sitzungSchreiben(wert).then(function () {
        dialogSchliessen();
        return sitzungAnzeigen().then(function () { return laufStarten(wert); });
      }).catch(function () {
        tokError.textContent =
          "Der Token liess sich auf diesem Geraet nicht ablegen " +
          "(privater Modus?). Ohne Ablage kein Start.";
        tokError.hidden = false;
      });
    });
  }

  // ---------------------------------------------------------- Menuepunkte

  var lockBtn = document.getElementById("lock-btn");
  var lockSub = document.getElementById("lock-sub");

  /** Der "Sperren"-Punkt sagt, ob es ueberhaupt etwas zu sperren gibt. */
  function sitzungAnzeigen() {
    return sitzungLesen().then(function (eintrag) {
      if (!lockBtn || !lockSub) { return eintrag; }
      if (eintrag) {
        var tage = Math.max(
          0,
          Math.ceil((eintrag.gueltig_bis - deps.jetzt()) / (24 * 60 * 60 * 1000))
        );
        lockSub.textContent =
          "Token gespeichert, noch " + tage + (tage === 1 ? " Tag" : " Tage");
        lockBtn.disabled = false;
      } else {
        lockSub.textContent = "Kein Token gespeichert";
        lockBtn.disabled = true;
      }
      return eintrag;
    });
  }

  var reloadBtn = document.getElementById("reload-btn");
  if (reloadBtn) {
    reloadBtn.addEventListener("click", function () {
      closeMenu();
      bannerZeigen("laeuft", "Daten werden geholt …", null);
      neuLaden().then(function () {
        bannerZeigen("fertig", "Daten aktualisiert.", null);
      }).catch(function (err) {
        bannerZeigen("fehler", "Neu laden ging nicht: " + err.message, null);
      });
    });
  }

  var recalcBtn = document.getElementById("recalc-btn");
  if (recalcBtn) {
    recalcBtn.addEventListener("click", function () {
      closeMenu();
      // Ohne Token passiert NICHTS Stilles: der Dialog geht auf, mehr nicht.
      sitzungLesen().then(function (eintrag) {
        if (!eintrag) { dialogOeffnen(null); return null; }
        return laufStarten(eintrag.token);
      });
    });
  }

  if (lockBtn) {
    lockBtn.addEventListener("click", function () {
      closeMenu();
      sitzungLoeschen().then(function () {
        return sitzungAnzeigen();
      }).then(function () {
        bannerZeigen("fertig", "Token verworfen. Beim naechsten Mal wird gefragt.", null);
      });
    });
  }

  // ------------------------------------------------------------ Live-Kurse
  //
  // Die Karten zeigen die Kurse aus dem Lauf. Diese Schicht legt AKTUELLE
  // Kurse darueber -- mehr nicht. Sie ruehrt Score, Rang und Ranking nicht
  // an; die stehen im eingefrorenen Monats-Ranking und haben mit dem
  // Tageskurs nichts zu tun.
  //
  // FAIL-SOFT ist hier die ganze Haltung: Ist der Dienst nicht erreichbar
  // oder liefert er etwas Unverstaendliches, wird der Punkt grau, der
  // Zeitstempel bleibt stehen, und die Karte zeigt weiter die Lauf-Kurse.
  // Kein zweiter Versuch ausser der Reihe -- der naechste kommt im
  // regulaeren Takt. Ein hakelnder Dienst darf keinen Anfragensturm ausloesen.

  var QUOTE_URL = "https://quote-proxy.easywebb.workers.dev";
  var TAKT_MS = 15000;

  /** Zahl aus einem beliebig verschachtelten Feld holen, tolerant. */
  function zahl(wert) {
    if (typeof wert === "number" && isFinite(wert)) { return wert; }
    if (typeof wert === "string") {
      var geputzt = wert.replace(/[%\s]/g, "").replace(",", ".");
      var n = parseFloat(geputzt);
      return isFinite(n) ? n : null;
    }
    return null;
  }

  function erstesFeld(daten, namen) {
    for (var i = 0; i < namen.length; i++) {
      if (daten && Object.prototype.hasOwnProperty.call(daten, namen[i])) {
        var n = zahl(daten[namen[i]]);
        if (n !== null) { return n; }
      }
    }
    return null;
  }

  /**
   * Kurs und Tagesaenderung aus der Antwort lesen — ohne festes Format.
   *
   * Das Antwortformat des Dienstes ist NICHT vertraglich zugesichert;
   * es wird aus der Antwort selbst abgelesen. Deshalb werden die
   * gebraeuchlichen Feldnamen der Reihe nach probiert, und eine
   * Verschachtelungsebene wird mitgenommen. Passt nichts, kommt null
   * zurueck -- und null heisst grau, nicht kaputt.
   */
  function leseKurs(daten) {
    if (!daten || typeof daten !== "object") { return null; }
    var kern = daten;
    var huellen = ["quote", "data", "result", "chart"];
    for (var i = 0; i < huellen.length; i++) {
      var innen = daten[huellen[i]];
      if (innen && typeof innen === "object" && !Array.isArray(innen)) {
        kern = innen;
        break;
      }
    }
    var preis = erstesFeld(kern, [
      "price", "regularMarketPrice", "last", "lastPrice", "c", "close", "kurs"
    ]);
    if (preis === null) { preis = erstesFeld(daten, ["price", "regularMarketPrice", "c"]); }
    if (preis === null) { return null; }

    var prozent = erstesFeld(kern, [
      "changePercent", "regularMarketChangePercent", "changesPercentage", "dp", "percent"
    ]);
    // Manche Dienste liefern nur den absoluten Vortagesschluss/Abstand.
    if (prozent === null) {
      var vortag = erstesFeld(kern, ["previousClose", "regularMarketPreviousClose", "pc"]);
      var diff = erstesFeld(kern, ["change", "regularMarketChange", "d"]);
      if (vortag !== null && vortag !== 0) {
        if (diff !== null) { prozent = (diff / vortag) * 100; }
        else { prozent = ((preis - vortag) / vortag) * 100; }
      }
    }
    return { preis: preis, prozent: prozent };
  }

  function deZahl(wert, stellen) {
    return wert.toFixed(stellen).replace(".", ",");
  }

  function uhrzeit(zeitpunkt) {
    var d = new Date(zeitpunkt);
    return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
  }

  var liveStand = {};   // Markt -> Zeitpunkt der letzten guten Antwort

  function liveAnzeigen(markt, gut) {
    var el = document.querySelector('[data-live="' + markt + '"]');
    if (!el) { return; }
    el.hidden = false;
    if (gut) { liveStand[markt] = deps.jetzt(); }
    var stand = liveStand[markt];
    el.className = "live" + (gut ? "" : " live--aus");
    el.querySelector(".live-txt").textContent =
      "Live · " + (stand ? uhrzeit(stand) : "—");
  }

  // Gesucht wird IMMER innerhalb der Markt-Sektion, nie global. Derselbe
  // Ticker kann in zwei Maerkten stehen; eine dokumentweite Suche wuerde
  // dann zweimal dieselbe Karte treffen und die andere nie.
  function kursSetzen(bereich, ticker, gelesen) {
    var wert = bereich.querySelector('[data-quote="' + ticker + '"]');
    if (!wert || !gelesen) { return false; }
    var waehrung = (wert.textContent.match(/^\S+/) || [""])[0];
    // Das Waehrungszeichen kommt aus der bestehenden Anzeige -- so bleibt
    // die Karte in ihrer eigenen Waehrung, ohne dass der Dienst eine
    // liefern muss.
    if (!/^[^0-9-]+$/.test(waehrung)) { waehrung = ""; }
    wert.textContent = waehrung + "\u00a0" + deZahl(gelesen.preis, 2);

    var aend = bereich.querySelector('[data-quote-change="' + ticker + '"]');
    if (aend) {
      if (gelesen.prozent === null) {
        aend.textContent = "";
        aend.className = "";
      } else {
        var vz = gelesen.prozent > 0 ? "+" : "";
        aend.textContent = vz + deZahl(gelesen.prozent, 1) + "\u00a0%";
        aend.className = gelesen.prozent > 0 ? "pos" : (gelesen.prozent < 0 ? "neg" : "");
      }
    }
    return true;
  }

  /** [{markt, bereich, tickers}] — je Markt-Sektion die sichtbaren Titel. */
  function sichtbareMaerkte() {
    var gefunden = [];
    var sektionen = document.querySelectorAll("section.market");
    for (var i = 0; i < sektionen.length; i++) {
      var live = sektionen[i].querySelector("[data-live]");
      if (!live) { continue; }
      var werte = sektionen[i].querySelectorAll("[data-quote]");
      var tickers = [];
      for (var j = 0; j < werte.length; j++) {
        tickers.push(werte[j].getAttribute("data-quote"));
      }
      gefunden.push({
        markt: live.getAttribute("data-live"),
        bereich: sektionen[i],
        tickers: tickers
      });
    }
    return gefunden;
  }

  /** Eine Runde: alle sichtbaren Titel je Markt einmal abfragen. */
  function liveRunde() {
    if (document.hidden) { return Promise.resolve("pausiert"); }
    var maerkte = sichtbareMaerkte();
    if (!maerkte.length) { return Promise.resolve("nichts zu tun"); }

    return Promise.all(maerkte.map(function (eintrag) {
      return Promise.all(eintrag.tickers.map(function (ticker) {
        return deps.netz(QUOTE_URL + "?ticker=" + encodeURIComponent(ticker))
          .then(function (antwort) {
            if (!antwort.ok) { return null; }
            return antwort.json();
          })
          .then(function (daten) {
            return kursSetzen(eintrag.bereich, ticker, leseKurs(daten));
          })
          .catch(function () { return false; });   // fail-soft, kein Nachfassen
      })).then(function (ergebnisse) {
        var gut = ergebnisse.some(function (x) { return x === true; });
        liveAnzeigen(eintrag.markt, gut);
        return gut;
      });
    })).then(function () { return "fertig"; });
  }

  var liveUhr = null;

  function liveStarten() {
    if (!document.querySelector("[data-live]")) { return; }
    liveRunde();
    if (liveUhr === null) {
      liveUhr = setInterval(liveRunde, TAKT_MS);
    }
  }

  // Unsichtbarer Tab fragt nichts ab: das spart Akku und Anfragen, und beim
  // Zurueckkommen wird sofort einmal aktualisiert statt bis zu 15 s zu warten.
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) { liveRunde(); }
  });

  liveStarten();

  // ============================================================== KONFLUENZ
  //
  // Zwei Werkzeuge nebeneinander. Es wird NICHTS verrechnet: kein
  // gemeinsamer Score, keine Wahrscheinlichkeit, keine Rangfolge der
  // Treffer. Die Treffer stehen alphabetisch -- eine Reihenfolge, die
  // nichts behauptet.
  //
  // FAIL-SOFT: Die Elliott-Daten sind eine fremde Datei auf einer fremden
  // Seite. Sind sie nicht da oder unlesbar, rendert die Momentum-Haelfte
  // normal weiter und daneben steht ein Hinweis. Kein Fehlerbild.

  var ELLIOTT_URL = "https://easywebb911.github.io/Elliott-Report/data/report.json";
  var ELLIOTT_SEITE = "https://easywebb911.github.io/Elliott-Report/";

  /** Elliott fuehrt die Maerkte gross, dieses Werkzeug klein. */
  function elliottSchluessel(markt) { return String(markt).toUpperCase(); }

  /** Erstes belegtes Feld aus einer Liste von Namen — tolerant. */
  function feld(objekt, namen, ersatz) {
    if (!objekt || typeof objekt !== "object") { return ersatz; }
    for (var i = 0; i < namen.length; i++) {
      var wert = objekt[namen[i]];
      if (wert !== undefined && wert !== null && wert !== "") { return wert; }
    }
    return ersatz;
  }

  /**
   * Die Long-Kandidaten eines Marktes aus dem Elliott-Bericht.
   *
   * Nur direction = long zaehlt: dieses Werkzeug ist long-only, ein
   * Short-Kandidat ist keine Ueberschneidung, sondern das Gegenteil.
   * Alles Uebrige wird tolerant gelesen; was fehlt, fehlt eben.
   */
  function elliottLong(bericht, markt) {
    if (!bericht || typeof bericht !== "object") { return []; }
    var maerkte = bericht.markets || bericht.maerkte;
    if (!maerkte || typeof maerkte !== "object") { return []; }
    var eintrag = maerkte[elliottSchluessel(markt)] || maerkte[markt];
    if (!eintrag || typeof eintrag !== "object") { return []; }
    var liste = eintrag.candidates || eintrag.kandidaten;
    if (!Array.isArray(liste)) { return []; }
    var raus = [];
    for (var i = 0; i < liste.length; i++) {
      var k = liste[i];
      if (!k || typeof k !== "object") { continue; }
      var ticker = feld(k, ["ticker", "symbol"], "");
      if (typeof ticker !== "string" || !ticker) { continue; }
      var richtung = String(feld(k, ["direction", "richtung"], "")).toLowerCase();
      if (richtung !== "long") { continue; }
      raus.push({
        ticker: ticker,
        name: String(feld(k, ["company_name", "name", "firma"], "")),
        score: feld(k, ["score", "confidence"], null),
        close: feld(k, ["close", "kurs", "price"], null)
      });
    }
    return raus;
  }

  /**
   * Der Abgleich. Rein, ohne Seiteneffekte, ohne Netz — und ohne jede
   * Verrechnung: die beiden Scores werden NEBENEINANDER gelegt, nie
   * zusammengefasst. Sortiert wird alphabetisch nach Ticker; jede andere
   * Reihenfolge waere eine Aussage darueber, welcher Treffer "besser" ist,
   * und die gibt es hier nicht.
   */
  function konfluenz(top5, longKandidaten) {
    var nachTicker = {};
    (longKandidaten || []).forEach(function (k) { nachTicker[k.ticker] = k; });
    var treffer = [];
    (top5 || []).forEach(function (m) {
      var e = nachTicker[m.ticker];
      if (!e) { return; }
      treffer.push({
        ticker: m.ticker,
        name: e.name || "",
        momentum_rang: m.rang,
        momentum_score: m.score,
        elliott_score: e.score
      });
    });
    treffer.sort(function (a, b) { return a.ticker < b.ticker ? -1 : (a.ticker > b.ticker ? 1 : 0); });
    return treffer;
  }

  function zahlOderStrich(wert, stellen) {
    var n = zahl(wert);
    return n === null ? "—" : deZahl(n, stellen);
  }

  function konfKarte(t) {
    return '<article class="card konf-treffer">' +
      '<div class="konf-kopf"><span class="ticker">' + sicher(t.ticker) + "</span>" +
      '<span class="cname">' + sicher(t.name || "—") + "</span></div>" +
      '<div class="metrics metrics--rang">' +
      '<div class="metric-box"><span class="m-val">' + t.momentum_rang + ". · " +
        zahlOderStrich(t.momentum_score, 1) + '</span>' +
        '<span class="m-lbl">Momentum: Rang · Score</span></div>' +
      '<div class="metric-box"><span class="m-val">' +
        zahlOderStrich(t.elliott_score, 1) + '</span>' +
        '<span class="m-lbl">Elliott: Score</span></div>' +
      "</div>" +
      '<p class="konf-links"><a href="./index.html">Momentum-Karte</a> · ' +
      '<a href="' + ELLIOTT_SEITE + '" target="_blank" rel="noopener noreferrer">Elliott-Report ↗</a></p>' +
      "</article>";
  }

  function sicher(text) {
    return String(text)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function liste(titel, eintraege, trefferTicker, wieViel) {
    var zeilen = (eintraege || []).map(function (x) {
      var markiert = trefferTicker.indexOf(x.ticker) >= 0;
      return '<li class="konf-zeile' + (markiert ? " konf-zeile--treffer" : "") + '">' +
        '<span class="konf-tick">' + sicher(x.ticker) + "</span>" +
        '<span class="konf-wert">' + wieViel(x) + "</span></li>";
    });
    if (!zeilen.length) { zeilen = ['<li class="konf-zeile konf-zeile--leer">—</li>']; }
    return '<div class="konf-spalte"><h4>' + sicher(titel) + "</h4><ul class=\"konf-liste\">" +
      zeilen.join("") + "</ul></div>";
  }

  function konfMarktBlock(markt, name, momentum, longs, stichtag) {
    var treffer = konfluenz(momentum, longs);
    var tickers = treffer.map(function (t) { return t.ticker; });
    var kopf = '<h2><span class="flag" aria-hidden="true">' +
      (markt === "us" ? "🇺🇸" : "🇩🇪") + "</span>" + sicher(name) + "</h2>";
    var meta = '<p class="market-meta">Momentum-Stichtag ' + sicher(stichtag || "—") + "</p>";
    var inhalt = treffer.length
      ? treffer.map(konfKarte).join("")
      : '<p class="konf-leer">' + sicher(LEER_TEXT) + "</p>";
    var gegenueber = '<div class="konf-spalten">' +
      liste("Momentum-Top-5", momentum, tickers, function (x) {
        return x.rang + ". · " + zahlOderStrich(x.score, 1);
      }) +
      liste("Elliott: Long-Kandidaten", longs, tickers, function (x) {
        return zahlOderStrich(x.score, 1);
      }) +
      "</div>";
    return '<section class="market">' + kopf + meta + inhalt + gegenueber + "</section>";
  }

  var LEER_TEXT =
    "Keine Überschneidung — das ist der Regelfall. Beide Werkzeuge messen " +
    "Verschiedenes; ein gemeinsamer Treffer ist selten.";

  function standText(objekt) {
    var wert = feld(objekt, ["generated_at", "erzeugt_am", "stand", "timestamp",
                             "as_of", "datum", "date"], null);
    return wert === null ? "Stand unbekannt" : String(wert);
  }

  function konfluenzAufbauen() {
    var ziel = document.getElementById("konf-inhalt");
    if (!ziel) { return Promise.resolve("keine Konfluenz-Seite"); }

    var eigenes = deps.netz("data/top5.json", { cache: "no-store" })
      .then(function (a) { return a.ok ? a.json() : null; })
      .catch(function () { return null; });
    var fremdes = deps.netz(ELLIOTT_URL, { cache: "no-store" })
      .then(function (a) { return a.ok ? a.json() : null; })
      .catch(function () { return null; });

    return Promise.all([eigenes, fremdes]).then(function (beide) {
      var mine = beide[0];
      var elliott = beide[1];

      var standM = document.getElementById("stand-momentum");
      var standE = document.getElementById("stand-elliott");
      var hinweis = document.getElementById("konf-hinweis");

      if (!mine || !mine.maerkte) {
        ziel.innerHTML = '<p class="konf-leer">Noch keine Momentum-Daten. ' +
          "Sie entstehen mit dem ersten Lauf.</p>";
        if (standM) { standM.textContent = "noch keine Daten"; }
        if (standE) { standE.textContent = elliott ? standText(elliott) : "nicht erreichbar"; }
        return "ohne momentum";
      }

      // Der Stand BEIDER Quellen. Sie laufen zu verschiedenen Zeiten.
      var staende = Object.keys(mine.maerkte).map(function (k) {
        return mine.maerkte[k].stichtag;
      });
      if (standM) { standM.textContent = "Stichtag " + (staende[0] || "—"); }
      if (standE) {
        standE.textContent = elliott ? standText(elliott) : "nicht erreichbar";
      }

      if (!elliott && hinweis) {
        hinweis.hidden = false;
        hinweis.textContent =
          "Elliott-Daten gerade nicht erreichbar. Die Momentum-Seite steht " +
          "vollständig; sobald die andere Quelle wieder antwortet, erscheinen " +
          "auch die Überschneidungen.";
      }

      var teile = [];
      ["us", "de"].forEach(function (markt) {
        var m = mine.maerkte[markt];
        if (!m) { return; }
        teile.push(konfMarktBlock(
          markt, m.name || markt.toUpperCase(), m.top5 || [],
          elliottLong(elliott, markt), m.stichtag
        ));
      });
      ziel.innerHTML = teile.join("");
      return elliott ? "fertig" : "ohne elliott";
    });
  }

  konfluenzAufbauen();

  sitzungAnzeigen();

  // Nach aussen nur, was die Tests brauchen. Kein Token, keine Ablage.
  window.MR = {
    deps: deps,
    neuLaden: neuLaden,
    laufStarten: laufStarten,
    verfolgen: verfolgen,
    sitzungLesen: sitzungLesen,
    sitzungSchreiben: sitzungSchreiben,
    sitzungLoeschen: sitzungLoeschen,
    sitzungAnzeigen: sitzungAnzeigen,
    dialogOeffnen: dialogOeffnen,
    bannerZeigen: bannerZeigen,
    leseKurs: leseKurs,
    liveRunde: liveRunde,
    liveAnzeigen: liveAnzeigen,
    QUOTE_URL: QUOTE_URL,
    TAKT_MS: TAKT_MS,
    konfluenz: konfluenz,
    elliottLong: elliottLong,
    konfluenzAufbauen: konfluenzAufbauen,
    ELLIOTT_URL: ELLIOTT_URL,
    LEER_TEXT: LEER_TEXT
  };
})();
