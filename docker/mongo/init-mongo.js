// MongoDB initialization script for RepoGPT app user
const dbName = process.env.MONGODB_DB || "repogpt";
const appUser = process.env.MONGO_APP_USER || "repogpt";
const appPassword = process.env.MONGO_APP_PASSWORD || "apppassword";

const targetDb = db.getSiblingDB(dbName);

targetDb.createUser({
  user: appUser,
  pwd: appPassword,
  roles: [
    { role: "readWrite", db: dbName },
    { role: "dbAdmin", db: dbName }
  ]
});

print(`Initialized RepoGPT database '${dbName}' and user '${appUser}'.`);
