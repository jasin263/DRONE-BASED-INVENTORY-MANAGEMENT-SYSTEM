export const canAccess = (roles: readonly string[], allowed: readonly string[]) =>
  roles.some((role) => allowed.includes(role));

export const canApprove = (roles: readonly string[]) =>
  canAccess(roles, ["Admin", "Inventory Controller"]);
