/**
 * JWT utilities with ECDSA (ES256) signing using Web Crypto API.
 * Supports key generation, rotation, and verification.
 */

interface JWTHeader {
  alg: "ES256";
  typ: "JWT";
  kid: string;
}

interface JWTPayload {
  sub: string;
  email: string;
  iat: number;
  exp: number;
  iss: string;
  aud: string;
  type?: "access" | "refresh";
}

interface JWTKey {
  id: string;
  kid: string;
  privateKey: string;
  publicKey: string;
  algorithm: string;
  isActive: boolean;
  createdAt: string;
  expiresAt: string | null;
}

const ISSUER = "arbbuilder";
const AUDIENCE = "arbbuilder-web";
const ACCESS_TOKEN_EXPIRY_MINUTES = 15;
const REFRESH_TOKEN_EXPIRY_DAYS = 7;

/**
 * Base64URL encode
 */
function base64UrlEncode(data: ArrayBuffer | Uint8Array | string): string {
  let bytes: Uint8Array;
  if (typeof data === "string") {
    bytes = new TextEncoder().encode(data);
  } else if (data instanceof ArrayBuffer) {
    bytes = new Uint8Array(data);
  } else {
    bytes = data;
  }

  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

/**
 * Base64URL decode
 */
function base64UrlDecode(str: string): Uint8Array {
  const base64 = str.replace(/-/g, "+").replace(/_/g, "/");
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const binary = atob(base64 + padding);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Generate random hex string
 */
function randomHex(bytes: number): string {
  const array = new Uint8Array(bytes);
  crypto.getRandomValues(array);
  return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Generate a new ECDSA P-256 key pair for JWT signing.
 */
export async function generateKeyPair(): Promise<{
  privateKeyJwk: JsonWebKey;
  publicKeyJwk: JsonWebKey;
}> {
  const keyPair = await crypto.subtle.generateKey(
    {
      name: "ECDSA",
      namedCurve: "P-256",
    },
    true, // extractable
    ["sign", "verify"]
  );

  const privateKeyJwk = await crypto.subtle.exportKey("jwk", keyPair.privateKey);
  const publicKeyJwk = await crypto.subtle.exportKey("jwk", keyPair.publicKey);

  return { privateKeyJwk, publicKeyJwk };
}

/**
 * Get or create the active signing key.
 */
export async function getActiveSigningKey(db: D1Database): Promise<JWTKey> {
  // Try to get the active key
  const activeKey = await db
    .prepare(
      `SELECT id, kid, private_key as privateKey, public_key as publicKey,
              algorithm, is_active as isActive, created_at as createdAt, expires_at as expiresAt
       FROM jwt_keys
       WHERE is_active = 1 AND (expires_at IS NULL OR expires_at > datetime('now'))
       ORDER BY created_at DESC
       LIMIT 1`
    )
    .first<JWTKey>();

  if (activeKey) {
    return activeKey;
  }

  // No active key, generate a new one
  return await rotateSigningKey(db);
}

/**
 * Rotate the signing key - creates a new key and marks old ones as inactive.
 */
export async function rotateSigningKey(db: D1Database): Promise<JWTKey> {
  const { privateKeyJwk, publicKeyJwk } = await generateKeyPair();

  const id = randomHex(16);
  const kid = `arb-${randomHex(8)}`;
  const now = new Date().toISOString();
  const expiresAt = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString(); // 90 days

  // Deactivate old keys
  await db
    .prepare(`UPDATE jwt_keys SET is_active = 0 WHERE is_active = 1`)
    .run();

  // Insert new key
  await db
    .prepare(
      `INSERT INTO jwt_keys (id, kid, private_key, public_key, algorithm, is_active, created_at, expires_at)
       VALUES (?, ?, ?, ?, 'ES256', 1, ?, ?)`
    )
    .bind(
      id,
      kid,
      JSON.stringify(privateKeyJwk),
      JSON.stringify(publicKeyJwk),
      now,
      expiresAt
    )
    .run();

  return {
    id,
    kid,
    privateKey: JSON.stringify(privateKeyJwk),
    publicKey: JSON.stringify(publicKeyJwk),
    algorithm: "ES256",
    isActive: true,
    createdAt: now,
    expiresAt,
  };
}

/**
 * Get a key by its kid for verification.
 */
export async function getKeyByKid(
  db: D1Database,
  kid: string
): Promise<JWTKey | null> {
  return await db
    .prepare(
      `SELECT id, kid, private_key as privateKey, public_key as publicKey,
              algorithm, is_active as isActive, created_at as createdAt, expires_at as expiresAt
       FROM jwt_keys
       WHERE kid = ? AND revoked_at IS NULL`
    )
    .bind(kid)
    .first<JWTKey>();
}

/**
 * Sign a JWT token with ECDSA.
 */
export async function signJWT(
  db: D1Database,
  payload: { sub: string; email: string },
  type: "access" | "refresh" = "access"
): Promise<string> {
  const key = await getActiveSigningKey(db);
  const privateKeyJwk = JSON.parse(key.privateKey) as JsonWebKey;

  // Import the private key
  const privateKey = await crypto.subtle.importKey(
    "jwk",
    privateKeyJwk,
    { name: "ECDSA", namedCurve: "P-256" },
    false,
    ["sign"]
  );

  const now = Math.floor(Date.now() / 1000);
  const exp = type === "access"
    ? now + ACCESS_TOKEN_EXPIRY_MINUTES * 60
    : now + REFRESH_TOKEN_EXPIRY_DAYS * 24 * 60 * 60;

  const header: JWTHeader = {
    alg: "ES256",
    typ: "JWT",
    kid: key.kid,
  };

  const jwtPayload: JWTPayload = {
    sub: payload.sub,
    email: payload.email,
    iat: now,
    exp,
    iss: ISSUER,
    aud: AUDIENCE,
    type,
  };

  const headerB64 = base64UrlEncode(JSON.stringify(header));
  const payloadB64 = base64UrlEncode(JSON.stringify(jwtPayload));
  const message = `${headerB64}.${payloadB64}`;

  const signature = await crypto.subtle.sign(
    { name: "ECDSA", hash: "SHA-256" },
    privateKey,
    new TextEncoder().encode(message)
  );

  const signatureB64 = base64UrlEncode(signature);

  return `${message}.${signatureB64}`;
}

/**
 * Create both access and refresh tokens.
 */
export async function createTokenPair(
  db: D1Database,
  payload: { sub: string; email: string }
): Promise<{ accessToken: string; refreshToken: string }> {
  const accessToken = await signJWT(db, payload, "access");
  const refreshToken = await signJWT(db, payload, "refresh");

  // Store refresh token hash in database
  const refreshTokenHash = await hashToken(refreshToken);
  const id = randomHex(16);
  const expiresAt = new Date(Date.now() + REFRESH_TOKEN_EXPIRY_DAYS * 24 * 60 * 60 * 1000).toISOString();

  await db
    .prepare(
      `INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at)
       VALUES (?, ?, ?, ?)`
    )
    .bind(id, payload.sub, refreshTokenHash, expiresAt)
    .run();

  return { accessToken, refreshToken };
}

/**
 * Hash a token for storage.
 */
async function hashToken(token: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(token);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Verify a refresh token and issue new token pair.
 */
export async function refreshTokens(
  db: D1Database,
  refreshToken: string
): Promise<{ accessToken: string; refreshToken: string } | null> {
  // Verify the refresh token JWT
  const payload = await verifyJWT(db, refreshToken);
  if (!payload || payload.type !== "refresh") {
    return null;
  }

  // Check if refresh token exists and is not revoked
  const tokenHash = await hashToken(refreshToken);
  const storedToken = await db
    .prepare(
      `SELECT id FROM refresh_tokens
       WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > datetime('now')`
    )
    .bind(tokenHash)
    .first<{ id: string }>();

  if (!storedToken) {
    return null;
  }

  // Revoke the old refresh token
  await db
    .prepare(`UPDATE refresh_tokens SET revoked_at = datetime('now') WHERE id = ?`)
    .bind(storedToken.id)
    .run();

  // Issue new token pair
  return createTokenPair(db, { sub: payload.sub, email: payload.email });
}

/**
 * Revoke all refresh tokens for a user.
 */
export async function revokeAllRefreshTokens(
  db: D1Database,
  userId: string
): Promise<void> {
  await db
    .prepare(`UPDATE refresh_tokens SET revoked_at = datetime('now') WHERE user_id = ? AND revoked_at IS NULL`)
    .bind(userId)
    .run();
}

/**
 * Verify a JWT token.
 */
export async function verifyJWT(
  db: D1Database,
  token: string
): Promise<JWTPayload | null> {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) {
      return null;
    }

    const [headerB64, payloadB64, signatureB64] = parts;

    // Decode header to get kid
    const headerJson = new TextDecoder().decode(base64UrlDecode(headerB64));
    const header = JSON.parse(headerJson) as JWTHeader;

    if (header.alg !== "ES256") {
      return null;
    }

    // Get the key by kid
    const key = await getKeyByKid(db, header.kid);
    if (!key) {
      return null;
    }

    const publicKeyJwk = JSON.parse(key.publicKey) as JsonWebKey;

    // Import the public key
    const publicKey = await crypto.subtle.importKey(
      "jwk",
      publicKeyJwk,
      { name: "ECDSA", namedCurve: "P-256" },
      false,
      ["verify"]
    );

    // Verify signature
    const message = `${headerB64}.${payloadB64}`;
    const signatureBytes = base64UrlDecode(signatureB64);
    // Convert to ArrayBuffer for crypto.subtle.verify
    const signatureBuffer = new ArrayBuffer(signatureBytes.length);
    new Uint8Array(signatureBuffer).set(signatureBytes);

    const valid = await crypto.subtle.verify(
      { name: "ECDSA", hash: "SHA-256" },
      publicKey,
      signatureBuffer,
      new TextEncoder().encode(message)
    );

    if (!valid) {
      return null;
    }

    // Decode and validate payload
    const payloadJson = new TextDecoder().decode(base64UrlDecode(payloadB64));
    const payload = JSON.parse(payloadJson) as JWTPayload;

    // Check expiration
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp < now) {
      return null;
    }

    // Check issuer and audience
    if (payload.iss !== ISSUER || payload.aud !== AUDIENCE) {
      return null;
    }

    return payload;
  } catch {
    return null;
  }
}

/**
 * Get JWKS (JSON Web Key Set) for public key distribution.
 */
export async function getJWKS(db: D1Database): Promise<{ keys: JsonWebKey[] }> {
  const keys = await db
    .prepare(
      `SELECT kid, public_key as publicKey
       FROM jwt_keys
       WHERE revoked_at IS NULL AND (expires_at IS NULL OR expires_at > datetime('now'))
       ORDER BY created_at DESC`
    )
    .all<{ kid: string; publicKey: string }>();

  const jwks = keys.results.map((key) => {
    const jwk = JSON.parse(key.publicKey) as JsonWebKey;
    return {
      ...jwk,
      kid: key.kid,
      use: "sig",
      alg: "ES256",
    };
  });

  return { keys: jwks };
}
