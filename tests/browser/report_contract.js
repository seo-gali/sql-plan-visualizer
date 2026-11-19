// Invoke with a Playwright page already at the prepared fixture server URL.
async (page) => {
  const assert = (value, message) => { if (!value) throw new Error(message); };
  const failures = [];
  const onError = error => failures.push(error.message);
  page.on("pageerror", onError);
  try {
    const reportURL = new URL("report.html", page.url()).href;
    const sourceURL = new URL("query.sql", reportURL).href;
    const response = await page.request.get(sourceURL);
    assert(response.ok(), "fixture SQL available");
    const sql = await response.text();
    await page.goto(reportURL);
    await page.locator("#language").selectOption("en");
    assert(await page.locator("#sql-source").textContent() === sql, "SQL source preserved");
    assert(await page.getByRole("heading", {name: "SQL Flow", exact: true}).isVisible(), "SQL Flow available");
    assert(await page.locator(".flow-node strong").getByText("Window", {exact: true}).count() === 1, "window computation shown");

    await page.locator("#language").focus();
    const token = page.locator("#sql-source .token").filter({hasText: "amount"}).first();
    const before = await token.evaluate(node => getComputedStyle(node).backgroundColor);
    await token.focus();
    const active = await token.evaluate(node => getComputedStyle(node).backgroundColor);
    assert(active !== before, "keyboard focus highlights source");
    const sourceID = await token.getAttribute("id");
    const reference = page.locator(`a[href="#${sourceID}"]`).first();
    assert(await reference.evaluate((node, color) => getComputedStyle(node.closest("tr")).backgroundColor === color, active), "matching reference highlighted");

    const recommendations = page.locator("section").filter({has: page.getByRole("heading", {name: "Recommendations", exact: true})});
    const evidence = recommendations.getByRole("link").first();
    const target = await evidence.getAttribute("href");
    await evidence.click();
    assert(new URL(page.url()).hash === target, "evidence link navigates to observed plan");
    assert(await page.locator(target).isVisible(), "observed plan target visible");

    await page.locator("#language").selectOption("ko");
    assert(await page.locator("html").getAttribute("lang") === "ko", "document language updated");
    assert(await page.getByRole("heading", {name: "SQL 원문", exact: true}).isVisible(), "Korean labels shown");
    assert(await page.locator(".flow-node strong").getByText("Window · 윈도 계산", {exact: true}).count() === 1, "window label translated");
    assert(await page.locator("#sql-source").textContent() === sql, "translation preserves SQL");
    assert(await page.evaluate(() => window.sqlpviInjected === undefined), "SQL payload never executes");

    await page.evaluate(() => {
      window.sqlpviCspViolations = [];
      document.addEventListener("securitypolicyviolation", event => window.sqlpviCspViolations.push(event.effectiveDirective));
      const injected = document.createElement("script");
      injected.textContent = "window.sqlpviCspBypass = true";
      document.body.appendChild(injected);
    });
    await page.waitForFunction(() => window.sqlpviCspViolations.some(directive => directive.startsWith("script-src")));
    assert(await page.evaluate(() => window.sqlpviCspBypass === undefined), "CSP blocks an untrusted script");

    const layouts = [];
    for (const width of [390, 1366]) {
      await page.setViewportSize({width, height: 900});
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      assert(!overflow, "no page overflow at " + width);
      layouts.push(width);
    }
    assert(await page.evaluate(() => performance.getEntriesByType("resource").length === 0), "no external resources");
    assert(failures.length === 0, "no browser runtime errors: " + failures.join("; "));
    return {source: "PASS", focus: "PASS", translation: "PASS", evidence: "PASS", injection: "PASS", csp: "PASS", layouts};
  } finally {
    page.off("pageerror", onError);
  }
}
