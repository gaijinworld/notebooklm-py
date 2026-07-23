
  (function() {
    "use strict";

    // Firebase App Configuration for Gamified Network Engineer App
    var firebaseConfig = {
      apiKey: "AIzaSyAr5oe2DNaYQseh2iYPvBucZvibKyqNLOc",
      authDomain: "gamified-network-engineer-app.firebaseapp.com",
      projectId: "gamified-network-engineer-app",
      storageBucket: "gamified-network-engineer-app.firebasestorage.app",
      messagingSenderId: "465331311664",
      appId: "1:465331311664:web:d558dfc8f83e81edcf89f5",
      measurementId: "G-DCFM1RVPP5"
    };

    if (window.firebase && !firebase.apps.length) {
      firebase.initializeApp(firebaseConfig);
      if (firebase.analytics) firebase.analytics();
    }

    var state = {
      user: null,
      apiUrl: localStorage.getItem("nblm_apiUrl") || "http://localhost:8000",
      apiToken: localStorage.getItem("nblm_apiToken") || "",
      notebooks: [],
      selectedNotebook: null,
      activeTab: "sources",
      tabData: {},
      selectedItemId: null,
    };

    var el = {
      authOverlay: document.getElementById("authOverlay"),
      btnGoogleAuth: document.getElementById("btnGoogleAuth"),
      authEmail: document.getElementById("authEmail"),
      authPassword: document.getElementById("authPassword"),
      togglePwdBtn: document.getElementById("togglePwdBtn"),
      btnSignInEmail: document.getElementById("btnSignInEmail"),
      btnCreateAccount: document.getElementById("btnCreateAccount"),
      btnForgotPassword: document.getElementById("btnForgotPassword"),
      userPill: document.getElementById("userPill"),
      userAvatar: document.getElementById("userAvatar"),
      userEmailText: document.getElementById("userEmailText"),
      btnSignOut: document.getElementById("btnSignOut"),
      settingsToggle: document.getElementById("settingsToggle"),
      settingsPanel: document.getElementById("settingsPanel"),
      apiUrl: document.getElementById("apiUrl"),
      apiToken: document.getElementById("apiToken"),
      testConnBtn: document.getElementById("testConnBtn"),
      connStatus: document.getElementById("connStatus"),
      notebookList: document.getElementById("notebookList"),
      refreshNotebooks: document.getElementById("refreshNotebooks"),
      tabBar: document.getElementById("tabBar"),
      tabContent: document.getElementById("tabContent"),
      generateBar: document.getElementById("generateBar"),
      generateType: document.getElementById("generateType"),
      generateBtn: document.getElementById("generateBtn"),
      paneDetail: document.getElementById("paneDetail"),
    };

    el.apiUrl.value = state.apiUrl;
    el.apiToken.value = state.apiToken;

    // Toggle Password Visibility
    el.togglePwdBtn.addEventListener("click", function() {
      var isPwd = el.authPassword.type === "password";
      el.authPassword.type = isPwd ? "text" : "password";
    });

    // Firebase Auth State Listener
    if (window.firebase && firebase.auth) {
      firebase.auth().onAuthStateChanged(function(user) {
        if (user) {
          state.user = user;
          onUserAuthenticated(user);
        } else {
          state.user = null;
          showAuthOverlay(true);
        }
      });
    }

    // Google Sign In via Firebase Auth Popup
    el.btnGoogleAuth.addEventListener("click", function() {
      if (!window.firebase || !firebase.auth) return;
      var provider = new firebase.auth.GoogleAuthProvider();
      provider.addScope("profile");
      provider.addScope("email");
      firebase.auth().signInWithPopup(provider).then(function(result) {
        var user = result.user;
        onUserAuthenticated(user);
      }).catch(function(err) {
        alert("Google Sign-In failed: " + err.message);
      });
    });

    // Email Sign In
    el.btnSignInEmail.addEventListener("click", function() {
      var email = el.authEmail.value.trim();
      var password = el.authPassword.value.trim();
      if (!email || !password) {
        alert("Please enter both email and password.");
        return;
      }
      if (!window.firebase || !firebase.auth) return;
      firebase.auth().signInWithEmailAndPassword(email, password).then(function(res) {
        onUserAuthenticated(res.user);
      }).catch(function(err) {
        alert("Sign in failed: " + err.message);
      });
    });

    // Create Account
    el.btnCreateAccount.addEventListener("click", function() {
      var email = el.authEmail.value.trim();
      var password = el.authPassword.value.trim();
      if (!email || !password) {
        alert("Please enter an email and password to create an account.");
        return;
      }
      if (!window.firebase || !firebase.auth) return;
      firebase.auth().createUserWithEmailAndPassword(email, password).then(function(res) {
        alert("Account created successfully!");
        onUserAuthenticated(res.user);
      }).catch(function(err) {
        alert("Account creation failed: " + err.message);
      });
    });

    // Forgot Password
    el.btnForgotPassword.addEventListener("click", function() {
      var email = el.authEmail.value.trim();
      if (!email) {
        alert("Please enter your email address to receive password reset instructions.");
        return;
      }
      if (!window.firebase || !firebase.auth) return;
      firebase.auth().sendPasswordResetEmail(email).then(function() {
        alert("Password reset email sent to " + email);
      }).catch(function(err) {
        alert("Error: " + err.message);
      });
    });

    // Sign Out
    el.btnSignOut.addEventListener("click", function() {
      if (window.firebase && firebase.auth) {
        firebase.auth().signOut().then(function() {
          showAuthOverlay(true);
        });
      } else {
        showAuthOverlay(true);
      }
    });

    function showAuthOverlay(show) {
      if (show) {
        el.authOverlay.classList.remove("hidden");
        el.userPill.style.display = "none";
        el.btnSignOut.style.display = "none";
      } else {
        el.authOverlay.classList.add("hidden");
        el.userPill.style.display = "flex";
        el.btnSignOut.style.display = "inline-block";
      }
    }

    function onUserAuthenticated(user) {
      showAuthOverlay(false);
      var email = user.email || user.displayName || "User";
      el.userEmailText.textContent = email;
      el.userAvatar.textContent = (email[0] || "U").toUpperCase();

      // Register/sync notebooklm-py in Cloud Firestore artifacts collection
      syncFirestoreArtifact(user);

      // Load user's Gemini / NotebookLM notebooks
      if (state.apiUrl) {
        testConnection();
      }
    }

    function syncFirestoreArtifact(user) {
      if (!window.firebase || !firebase.firestore) return;
      try {
        var db = firebase.firestore();
        db.collection("artifacts").doc("notebooklm-py").set({
          name: "notebooklm-py",
          title: "NotebookLM Py",
          description: "Google Gemini NotebookLM Py Integration Artifact for Gamified Network Engineer App",
          url: "http://gaijinworld-local.local/notebooklm-py/",
          status: "active",
          projectId: "gamified-network-engineer-app",
          projectNumber: "465331311664",
          parentOrg: "gaijinworld.com",
          connectedUser: {
            uid: user.uid,
            email: user.email,
            displayName: user.displayName || user.email,
            photoURL: user.photoURL || null
          },
          updatedAt: firebase.firestore.FieldValue.serverTimestamp()
        }, { merge: true }).then(function() {
          console.log("Firestore artifact 'notebooklm-py' synced successfully.");
        }).catch(function(e) {
          console.warn("Firestore sync notice:", e);
        });
      } catch(e) {
        console.warn("Firestore sync warning:", e);
      }
    }

    el.settingsToggle.addEventListener("click", function() {
      el.settingsPanel.classList.toggle("open");
    });

    el.apiUrl.addEventListener("change", function() {
      state.apiUrl = el.apiUrl.value.trim().replace(/\/+$/, "");
      localStorage.setItem("nblm_apiUrl", state.apiUrl);
    });
    el.apiToken.addEventListener("change", function() {
      state.apiToken = el.apiToken.value.trim();
      localStorage.setItem("nblm_apiToken", state.apiToken);
    });

    el.testConnBtn.addEventListener("click", testConnection);
    el.refreshNotebooks.addEventListener("click", loadNotebooks);

    el.tabBar.addEventListener("click", function(e) {
      var tab = e.target.closest(".tab");
      if (!tab) return;
      switchTab(tab.dataset.tab);
    });

    el.generateBtn.addEventListener("click", generateArtifact);

    function api(method, path, body) {
      var url = state.apiUrl + "/v1" + path;
      var headers = { "Accept": "application/json" };
      if (state.apiToken) headers["Authorization"] = "Bearer " + state.apiToken;
      if (body) {
        headers["Content-Type"] = "application/json";
        if (typeof body === "object") body = JSON.stringify(body);
      }
      return fetch(url, { method: method, headers: headers, body: body })
        .then(function(resp) {
          if (resp.status === 204) return null;
          if (resp.status >= 400) {
            return resp.json().then(function(err) {
              throw new Error(err.detail || err.message || ("HTTP " + resp.status));
            });
          }
          var ct = resp.headers.get("content-type") || "";
          if (ct.includes("application/json")) return resp.json();
          if (ct.includes("text/")) return resp.text();
          return resp.blob();
        });
    }

    function testConnection() {
      el.connStatus.textContent = "Testing...";
      el.connStatus.className = "conn-status";
      api("GET", "/notebooks").then(function(data) {
        var count = (data.notebooks || []).length;
        el.connStatus.textContent = "Connected (" + count + " notebooks)";
        el.connStatus.className = "conn-status ok";
        loadNotebooks();
      }).catch(function(err) {
        el.connStatus.textContent = err.message;
        el.connStatus.className = "conn-status err";
      });
    }

    function loadNotebooks() {
      el.notebookList.innerHTML = '<div class="loading">Loading user\'s notebooks...</div>';
      api("GET", "/notebooks").then(function(data) {
        state.notebooks = data.notebooks || [];
        renderNotebooks();
      }).catch(function(err) {
        el.notebookList.innerHTML = '<div class="error-msg">' + escapeHtml(err.message) + "</div>";
      });
    }

    function renderNotebooks() {
      if (!state.notebooks.length) {
        el.notebookList.innerHTML = '<div class="empty-state"><p>No Google Gemini notebooks found for this user.</p></div>';
        return;
      }
      var html = state.notebooks.map(function(nb) {
        var id = nb.id || nb.notebook_id || "";
        var title = nb.title || "Untitled Notebook";
        var active = state.selectedNotebook === id ? " active" : "";
        var meta = nb.source_count != null ? nb.source_count + " sources" : "";
        return '<div class="notebook-item' + active + '" data-id="' + escapeAttr(id) + '">' +
          '<div class="nb-title">' + escapeHtml(title) + "</div>" +
          (meta ? '<div class="nb-meta">' + escapeHtml(meta) + "</div>" : "") +
          "</div>";
      }).join("");
      el.notebookList.innerHTML = html;
      el.notebookList.querySelectorAll(".notebook-item").forEach(function(item) {
        item.addEventListener("click", function() {
          selectNotebook(item.dataset.id);
        });
      });
    }

    function selectNotebook(id) {
      state.selectedNotebook = id;
      state.selectedItemId = null;
      renderNotebooks();
      loadTabData(state.activeTab);
      el.generateBar.style.display = state.activeTab === "artifacts" ? "flex" : "none";
    }

    function switchTab(tab) {
      state.activeTab = tab;
      state.selectedItemId = null;
      el.tabBar.querySelectorAll(".tab").forEach(function(t) {
        t.classList.toggle("active", t.dataset.tab === tab);
      });
      el.generateBar.style.display = tab === "artifacts" ? "flex" : "none";
      if (state.selectedNotebook) {
        loadTabData(tab);
      } else {
        el.tabContent.innerHTML = '<div class="empty-state"><p>Select a notebook first.</p></div>';
      }
    }

    function loadTabData(tab) {
      if (!state.selectedNotebook) return;
      var nb = state.selectedNotebook;
      el.tabContent.innerHTML = '<div class="loading">Loading ' + tab + "...</div>";
      var path;
      if (tab === "sources") path = "/notebooks/" + nb + "/sources";
      else if (tab === "artifacts") path = "/notebooks/" + nb + "/artifacts";
      else if (tab === "notes") path = "/notebooks/" + nb + "/notes";
      else if (tab === "research") path = "/notebooks/" + nb + "/research";
      else return;
      api("GET", path).then(function(data) {
        state.tabData[tab] = data;
        renderTabList(tab, data);
      }).catch(function(err) {
        el.tabContent.innerHTML = '<div class="error-msg">' + escapeHtml(err.message) + "</div>";
      });
    }

    function renderTabList(tab, data) {
      var items = data[tab] || data.artifacts || data.sources || data.notes || data.research_runs || [];
      if (!items.length) {
        el.tabContent.innerHTML = '<div class="empty-state"><p>No ' + escapeHtml(tab) + ' found.</p></div>';
        return;
      }
      var html = items.map(function(item) {
        var id = item.id || item.source_id || item.artifact_id || item.note_id || item.run_id || item.task_id || "";
        var title = item.title || item.name || item.kind || item.type || "Untitled";
        var active = state.selectedItemId === id ? " active" : "";
        var metaHtml = "";
        if (tab === "sources") {
          var kind = item.kind || item.source_kind || "unknown";
          var status = item.status || item.state || "ready";
          metaHtml = '<div class="li-meta"><span class="badge kind">' + escapeHtml(kind) + "</span>" +
            '<span class="badge ' + statusClass(status) + '">' + escapeHtml(status) + "</span></div>";
        } else if (tab === "artifacts") {
          var kind2 = item.kind || item.type || "artifact";
          var status2 = item.status || item.state || "unknown";
          metaHtml = '<div class="li-meta"><span class="badge kind">' + escapeHtml(kind2) + "</span>" +
            '<span class="badge ' + statusClass(status2) + '">' + escapeHtml(status2) + "</span></div>";
        } else if (tab === "notes") {
          var preview = (item.content_preview || item.content || "").substring(0, 60);
          metaHtml = '<div class="li-meta">' + escapeHtml(preview) + "...</div>";
        } else if (tab === "research") {
          var st = item.status || item.state || "unknown";
          metaHtml = '<div class="li-meta"><span class="badge ' + statusClass(st) + '">' + escapeHtml(st) + "</span></div>";
        }
        return '<div class="list-item' + active + '" data-id="' + escapeAttr(id) + '">' +
          '<div class="li-title">' + escapeHtml(title) + "</div>" + metaHtml + "</div>";
      }).join("");
      el.tabContent.innerHTML = html;
      el.tabContent.querySelectorAll(".list-item").forEach(function(item) {
        item.addEventListener("click", function() {
          state.selectedItemId = item.dataset.id;
          el.tabContent.querySelectorAll(".list-item").forEach(function(i) { i.classList.remove("active"); });
          item.classList.add("active");
          renderDetail(tab, item.dataset.id);
        });
      });
    }

    function renderDetail(tab, itemId) {
      var items = state.tabData[tab] || [];
      var items2 = items[tab] || items.artifacts || items.sources || items.notes || items.research_runs || items;
      if (!Array.isArray(items2)) items2 = [];
      var item = items2.find(function(i) {
        var id = i.id || i.source_id || i.artifact_id || i.note_id || i.run_id || i.task_id || "";
        return id === itemId;
      });
      if (!item) {
        el.paneDetail.innerHTML = '<div class="empty-state"><p>Item not found.</p></div>';
        return;
      }
      var html = '<div class="detail-card"><h3>' + escapeHtml(item.title || item.name || item.kind || "Detail") + "</h3>";
      var skipKeys = { title: true, name: true };
      for (var key in item) {
        if (skipKeys[key] || !Object.prototype.hasOwnProperty.call(item, key)) continue;
        var val = item[key];
        if (val === null || val === undefined) continue;
        if (typeof val === "object") val = JSON.stringify(val, null, 2);
        if (typeof val === "string" && val.length > 200) {
          html += '<div class="field"><span class="field-label">' + escapeHtml(key) + ':</span></div>';
          html += "<pre>" + escapeHtml(val) + "</pre>";
        } else {
          html += '<div class="field"><span class="field-label">' + escapeHtml(key) + ':</span> <span class="field-value">' + escapeHtml(String(val)) + "</span></div>";
        }
      }
      if (tab === "artifacts" && (item.status === "completed" || item.state === "COMPLETED")) {
        var dlPath = "/notebooks/" + state.selectedNotebook + "/artifacts/" + itemId + "/download";
        html += '<div style="margin-top:0.75rem;"><button class="settings-btn" onclick="window.NBLM.downloadArtifact(\'' + escapeAttr(dlPath) + "')\">Download</button></div>";
      }
      html += "</div>";
      el.paneDetail.innerHTML = html;
    }

    function generateArtifact() {
      if (!state.selectedNotebook) return;
      var kind = el.generateType.value;
      el.generateBtn.disabled = true;
      el.generateBtn.textContent = "Generating...";
      api("POST", "/notebooks/" + state.selectedNotebook + "/artifacts", { type: kind }).then(function(data) {
        el.generateBtn.disabled = false;
        el.generateBtn.textContent = "Generate";
        el.paneDetail.innerHTML = '<div class="detail-card"><h3>Generation Started</h3>' +
          '<div class="field"><span class="field-label">Type:</span> <span class="field-value">' + escapeHtml(kind) + "</span></div>" +
          '<div class="field"><span class="field-label">Task ID:</span> <span class="field-value">' + escapeHtml(data.task_id || data.id || "") + "</span></div>" +
          '<div class="field"><span class="field-label">Status:</span> <span class="field-value">Pending - poll the Artifacts tab to check progress.</span></div>' +
          "</div>";
        setTimeout(function() { loadTabData("artifacts"); }, 2000);
      }).catch(function(err) {
        el.generateBtn.disabled = false;
        el.generateBtn.textContent = "Generate";
        el.paneDetail.innerHTML = '<div class="error-msg">' + escapeHtml(err.message) + "</div>";
      });
    }

    function downloadArtifact(path) {
      var url = state.apiUrl + "/v1" + path;
      fetch(url, { headers: { "Authorization": "Bearer " + state.apiToken } })
        .then(function(r) { return r.blob(); })
        .then(function(blob) {
          var u = URL.createObjectURL(blob);
          var a = document.createElement("a");
          a.href = u;
          a.download = "";
          a.click();
          URL.revokeObjectURL(u);
        })
        .catch(function(err) {
          el.paneDetail.innerHTML = '<div class="error-msg">Download failed: ' + escapeHtml(err.message) + "</div>";
        });
    }

    function statusClass(s) {
      s = (s || "").toLowerCase();
      if (s === "ready" || s === "completed" || s === "done") return "ready";
      if (s === "pending" || s === "in_progress" || s === "processing" || s === "running") return "pending";
      if (s === "failed" || s === "error") return "failed";
      return "ready";
    }

    function escapeHtml(s) {
      var d = document.createElement("div");
      d.textContent = s == null ? "" : String(s);
      return d.innerHTML;
    }
    function escapeAttr(s) {
      return escapeHtml(s).replace(/"/g, "&quot;");
    }

    window.NBLM = { downloadArtifact: downloadArtifact };
  })();
  