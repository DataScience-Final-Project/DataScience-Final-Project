import { Column, DataType, Model, PrimaryKey, Table } from "sequelize-typescript";
import type { Optional } from "sequelize";

export type SearchFilters = {
    city?: string;
    slider?: [number, number];
    yearsForward?: string;
};

type SavedSearchAttributes = {
    id: number;
    userId: number;
    name: string;
    filters: SearchFilters;
    createdAt: Date;
};

type SavedSearchCreationAttributes = Optional<SavedSearchAttributes, 'id' | 'createdAt'>;

@Table({
    tableName: 'saved_searches',
    timestamps: true,
    createdAt: 'created_at',
    updatedAt: false,
})
export class SavedSearch extends Model<SavedSearchAttributes, SavedSearchCreationAttributes> {
    @PrimaryKey
    @Column({ type: DataType.BIGINT, autoIncrement: true })
    declare id: number;

    @Column({ type: DataType.BIGINT, allowNull: false, field: 'user_id' })
    declare userId: number;

    @Column({ type: DataType.TEXT, allowNull: false })
    declare name: string;

    @Column({ type: DataType.JSONB, allowNull: false })
    declare filters: SearchFilters;

    @Column({ type: DataType.DATE, field: 'created_at' })
    declare createdAt: Date;
}
