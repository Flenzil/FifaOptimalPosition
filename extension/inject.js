let visitedFutBinTriggered = false;
if (window.location.hostname.includes("futbin")) {
  if (window.location.pathname === "/squad-builder") {
    if (!visitedFutBinTriggered) {
      visitedFutBinTriggered = true;
      alert("YO WELCOME TO FUTBIN BOI");

      document
        .getElementsByClassName("site-builder-24-page")[0]
        .append("<h1>test</h1>");
    }
  }
}
