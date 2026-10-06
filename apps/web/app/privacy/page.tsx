import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy notice | IkonetU", robots: { index: false } };

export default function Privacy() {
  return (
    <main className="wrap prose">
      <p><a href="/">Back to IkonetU</a></p>
      <h1>Privacy notice</h1>
      <p><strong>This is a draft. A lawyer will review it before sign-up opens to the public.</strong></p>
      <h2>Who we are</h2>
      <p>IkonetU Technology Limited is registered in England and Wales, company number 17110122. We run the IkonetU platform for founders in Nigeria, Ghana and Kenya.</p>
      <h2>What we collect on the waitlist</h2>
      <p>We collect your name, your phone number or email, your country, the role you are joining as, your confirmation that you are 18 or older, and the date you joined.</p>
      <h2>What we collect when you create an account</h2>
      <p>We collect the email address or phone number you sign in with, your full name, your country, your confirmation that you are 18 or older, and the date you agreed to this notice. If you give them, we also collect your city, institution, student or graduate status and a short bio. We collect your venture&apos;s name, sector, stage and country, and its description, website and social media links if you give them.</p>
      <h2>Your choices</h2>
      <p>When you create your profile you choose, one by one, whether we may check the evidence you submit, look up your company in the official registry, read your business bank statements when you connect an account, and send you notifications. We record each answer with the date and the version of this notice. A check only runs when you have said yes to it.</p>
      <h2>Who can see your account details</h2>
      <p>Other signed-in members can see your name, country, city, institution, bio and venture. They cannot see your email address or phone number.</p>
      <h2>Why we collect it</h2>
      <p>We use waitlist details only to tell you when Season 1 opens in your country. We use account details to run your account and your venture&apos;s profile. We do not sell either or share them for advertising.</p>
      <h2>Where we keep it and for how long</h2>
      <p>Our database runs on Supabase. We will set how long we keep waitlist and account details before sign-up opens, and we will state those periods here.</p>
      <h2>Your rights</h2>
      <p>The Nigeria Data Protection Act 2023, the Kenya Data Protection Act 2019 and the Ghana Data Protection Act 2012 give you the right to see, correct and delete your details. You can also withdraw your consent at any time.</p>
      <h2 id="contact">Contact</h2>
      <p>To use any of these rights, contact us at the address we will publish here before launch.</p>
    </main>
  );
}
