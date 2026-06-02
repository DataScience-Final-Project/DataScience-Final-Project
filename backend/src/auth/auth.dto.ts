export type SignupRequest = {
    email?: string;
    phone?: string;
    username?: string;
    firstName?: string;
    lastName?: string;
    first_name?: string;
    last_name?: string;
    password?: string;
};

export type LoginRequest = {
    identifier?: string;
    email?: string;
    username?: string;
    phone?: string;
    password?: string;
};
