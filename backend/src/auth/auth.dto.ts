export type SignupRequest = {
    email?: string;
    phone?: string;
    username?: string;
    password?: string;
};

export type LoginRequest = {
    identifier?: string;
    email?: string;
    username?: string;
    phone?: string;
    password?: string;
};
