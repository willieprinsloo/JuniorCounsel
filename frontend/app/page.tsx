import { redirect } from "next/navigation";

export default function Home() {
  // Redirect to cases (landing page) - auth middleware will handle redirecting to login if needed
  redirect("/cases");
}
