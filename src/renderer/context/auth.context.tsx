import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { User } from "src/types/auth";

type States = {
  user: User | null;
  setUser: (user: User) => void;
  users: User[];
  refreshUsers: () => void;
};

export const AuthContext = createContext<States>({
  refreshUsers: () => {},
  user: null,
  users: [],
  setUser: () => {},
});

export const AuthContextProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  // Default user without authentication
  const defaultUser: User = {
    name: "Default User",
    role: "Admin",
    logged: true,
  };
  
  const [user, setUser] = useState<User | null>(defaultUser);
  const [users, setUsers] = useState<User[]>([defaultUser]);

  const authenticateUser = useCallback(() => {
    // Skip authentication, always use default user
    setUser(defaultUser);
  }, []);

  const refreshUsers = useCallback(async () => {
    // Skip fetching users from API
    setUsers([defaultUser]);
  }, []);

  useEffect(() => {
    refreshUsers();
  }, [refreshUsers]);

  useEffect(() => {
    authenticateUser();
  }, [authenticateUser]);
  const values = useMemo(
    () => ({
      user,
      users,
      refreshUsers,
      setUser,
    }),
    [user, users, refreshUsers],
  );
  return <AuthContext.Provider value={values}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within a AuthProvider");
  }
  return ctx;
};
