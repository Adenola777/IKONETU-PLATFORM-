"use client";

import { useEffect, useState } from "react";

/**
 * A hidden field carrying a key made when the form is shown. Sending the form
 * twice sends the same key, so the server saves the submission once. The key
 * is made in the browser after the page loads, so the server's copy of the page
 * and the browser's agree; a form sent before that carries no key and is saved
 * as before.
 */
export function RequestKey() {
  const [key, setKey] = useState("");
  useEffect(() => {
    setKey(crypto.randomUUID());
  }, []);
  return <input type="hidden" name="requestKey" value={key} />;
}
