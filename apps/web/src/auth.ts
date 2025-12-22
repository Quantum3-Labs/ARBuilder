import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";
import Google from "next-auth/providers/google";
import { D1Adapter } from "@auth/d1-adapter";

// Get the Cloudflare environment from the request context
function getCloudflareEnv(): Cloudflare.Env {
  // This will be injected by the Cloudflare runtime
  return (globalThis as unknown as { process: { env: Cloudflare.Env } }).process?.env ?? {} as Cloudflare.Env;
}

export const { handlers, signIn, signOut, auth } = NextAuth(() => {
  const env = getCloudflareEnv();

  return {
    adapter: D1Adapter(env.DB),
    providers: [
      GitHub({
        clientId: env.AUTH_GITHUB_ID,
        clientSecret: env.AUTH_GITHUB_SECRET,
      }),
      Google({
        clientId: env.AUTH_GOOGLE_ID,
        clientSecret: env.AUTH_GOOGLE_SECRET,
      }),
    ],
    callbacks: {
      session({ session, user }) {
        if (session.user) {
          session.user.id = user.id;
        }
        return session;
      },
    },
    pages: {
      signIn: "/login",
    },
  };
});
