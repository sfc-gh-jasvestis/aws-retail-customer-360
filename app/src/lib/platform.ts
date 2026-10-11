// Build option, set in the SPCS spec (snowflake/07_deploy_app.sql):
// 'snowflake' = Snowflake-only build (native engagement simulator, Cortex AI_COMPLETE memo);
// 'aws' = AWS + Snowflake build (Firehose/S3/Snowpipe feed, Bedrock memo, QuickSight).
export type DemoPlatform = 'snowflake' | 'aws';

export const demoPlatform = (): DemoPlatform => (process.env.DEMO_PLATFORM === 'snowflake' ? 'snowflake' : 'aws');
