import Store from "electron-store";
import os from "os";
import { User } from "../types/auth";

type TypedStore = {
  uvOptionalGroups: string[];
  users: User[];
};

export const store = new Store<TypedStore>({
  defaults: {
    uvOptionalGroups: [],
    users: [
      {
        name: os.userInfo().username,
        role: "Admin",
        logged: true,
      },
    ],
  },
});
