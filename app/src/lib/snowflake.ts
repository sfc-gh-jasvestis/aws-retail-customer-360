import snowflake from 'snowflake-sdk';

let connection: any = null;

/**
 * The in-flight connect attempt.
 *
 * `createConnection()` returns a handle SYNCHRONOUSLY, long before `connect()`
 * completes. Guarding only on the handle therefore hands a not-yet-connected
 * object to every concurrent caller. A single dashboard request fires a dozen
 * parallel queries, which opened a dozen connections and silently failed some of
 * them - the symptom was a route field quietly coming back empty.
 *
 * Memoising the PROMISE means all concurrent callers await the same connect.
 */
let connecting: Promise<any> | null = null;

function resetConnection() {
  connection = null;
  connecting = null;
}

/**
 * Reads an environment variable at request time.
 *
 * Next.js/webpack statically replaces literal `process.env.FOO` member
 * expressions at build time. Because these values only exist inside the SPCS
 * container at runtime, that inlining baked empty strings into the image and
 * every connection failed with "Invalid account". Looking the name up through
 * a computed key on globalThis defeats that substitution.
 */
function env(name: string): string {
  const proc: any = (globalThis as any).process;
  if (!proc || !proc.env) return '';
  return proc.env[name] || '';
}

/**
 * Reads the OAuth token that Snowpark Container Services writes into the
 * container. Snowflake refreshes this file every few minutes, so it must be
 * read at connect time rather than cached at module load.
 */
function getOAuthToken(): string {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const fs = require('fs');
    return fs.readFileSync('/snowflake/session/token', 'utf8').trim();
  } catch {
    // Not running in SPCS - fall back to an explicitly supplied token.
    return env('SNOWFLAKE_TOKEN');
  }
}

/** Base URL and auth headers for Snowflake REST APIs (Cortex Agents). */
export function restAuth(): { baseUrl: string; headers: Record<string, string> } {
  const host = env('SNOWFLAKE_HOST') || `${env('SNOWFLAKE_ACCOUNT')}.snowflakecomputing.com`;
  const pat = env('SNOWFLAKE_AUTHENTICATOR') === 'PROGRAMMATIC_ACCESS_TOKEN';
  return {
    baseUrl: `https://${host}`,
    headers: {
      Authorization: `Bearer ${getOAuthToken()}`,
      'X-Snowflake-Authorization-Token-Type': pat ? 'PROGRAMMATIC_ACCESS_TOKEN' : 'OAUTH',
    },
  };
}

export function databaseName(): string {
  return env('SNOWFLAKE_DATABASE') || env('DATABASE');
}

export async function getConnection() {
  if (connection) return connection;
  // Await an in-flight connect rather than starting a second one.
  if (connecting) return connecting;

  const options: Record<string, any> = {
    // SPCS injects these. The OAuth token is only valid when paired with host.
    account: env('SNOWFLAKE_ACCOUNT'),
    host: env('SNOWFLAKE_HOST'),
    database: env('SNOWFLAKE_DATABASE') || env('DATABASE'),
    schema: env('SNOWFLAKE_SCHEMA') || env('SCHEMA') || 'CURATED',
    // SPCS: OAUTH with the container token. Local runs may set
    // SNOWFLAKE_AUTHENTICATOR=PROGRAMMATIC_ACCESS_TOKEN and SNOWFLAKE_TOKEN.
    authenticator: env('SNOWFLAKE_AUTHENTICATOR') || 'OAUTH',
    token: getOAuthToken(),
    clientSessionKeepAlive: true,
  };

  // Not injected by SPCS. Omit entirely so the service QUERY_WAREHOUSE applies.
  const warehouse = env('SNOWFLAKE_WAREHOUSE') || env('WAREHOUSE');
  if (warehouse) options.warehouse = warehouse;
  // Only needed for local PAT runs; SPCS derives both from the service token.
  if (env('SNOWFLAKE_USER')) options.username = env('SNOWFLAKE_USER');
  if (env('SNOWFLAKE_ROLE')) options.role = env('SNOWFLAKE_ROLE');

  const handle = snowflake.createConnection(options as any);

  connecting = new Promise((resolve, reject) => {
    handle.connect((err: any, conn: any) => {
      if (err) {
        // Drop everything so the next request retries with a fresh token.
        resetConnection();
        reject(err);
      } else {
        // Publish the handle only now that it is usable.
        connection = conn || handle;
        connecting = null;
        resolve(connection);
      }
    });
  });

  return connecting;
}

export async function executeQuery<T = Record<string, any>>(sql: string, binds: (string | number)[] = []): Promise<T[]> {
  const conn = await getConnection();
  return new Promise((resolve, reject) => {
    conn.execute({
      sqlText: sql,
      binds,
      complete: (err: any, _stmt: any, rows: T[]) => {
        if (err) {
          // A dead session must not poison every later request.
          resetConnection();
          reject(err);
        } else {
          resolve(rows || []);
        }
      },
    });
  });
}

