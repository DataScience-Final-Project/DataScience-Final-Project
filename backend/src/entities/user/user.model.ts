import { Column, DataType, Model, PrimaryKey, Table } from "sequelize-typescript";
import type { Optional } from "sequelize";

type UserAttributes = {
    userId: number;
    email: string;
    phone: string;
    username: string;
    firstName: string;
    lastName: string;
    passwordHash: string;
    passwordSalt: string;
    passwordAlgorithm: string;
    createdAt: Date;
    updatedAt: Date;
};

type UserCreationAttributes = Optional<UserAttributes, 'userId' | 'createdAt' | 'updatedAt' | 'passwordAlgorithm'>;

@Table({
    tableName: 'users',
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: 'updated_at',
})
export class User extends Model<UserAttributes, UserCreationAttributes> {
    @PrimaryKey
    @Column({ type: DataType.BIGINT, autoIncrement: true, field: 'user_id' })
    declare userId: number;

    @Column({ type: DataType.TEXT, allowNull: false, unique: true })
    declare email: string;

    @Column({ type: DataType.TEXT, allowNull: false, unique: true })
    declare phone: string;

    @Column({ type: DataType.TEXT, allowNull: false, unique: true })
    declare username: string;

    @Column({ type: DataType.TEXT, allowNull: false, field: 'first_name' })
    declare firstName: string;

    @Column({ type: DataType.TEXT, allowNull: false, field: 'last_name' })
    declare lastName: string;

    @Column({ type: DataType.TEXT, allowNull: false, field: 'password_hash' })
    declare passwordHash: string;

    @Column({ type: DataType.TEXT, allowNull: false, field: 'password_salt' })
    declare passwordSalt: string;

    @Column({ type: DataType.TEXT, allowNull: false, field: 'password_algorithm' })
    declare passwordAlgorithm: string;

    @Column({ type: DataType.DATE, field: 'created_at' })
    declare createdAt: Date;

    @Column({ type: DataType.DATE, field: 'updated_at' })
    declare updatedAt: Date;
}
