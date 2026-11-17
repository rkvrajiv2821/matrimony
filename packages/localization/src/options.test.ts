/**
 * Every option code the API can return must have a label in every language.
 * Codes are read from the generated OpenAPI schema, so adding a code on the server
 * without translating it fails CI.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const openapi = JSON.parse(
  readFileSync(new URL("../../api-client/openapi.json", import.meta.url), "utf8"),
) as { components: { schemas: Record<string, { enum?: string[] }> } };

// localization group -> OpenAPI enum schema
const GROUPS: Record<string, string> = {
  created_for: "CreatedFor",
  gender: "Gender",
  marital_status: "MaritalStatus",
  physical_status: "PhysicalStatus",
  language: "SpokenLanguage",
  diet: "Diet",
  habit: "Habit",
  family_type: "FamilyType",
  family_values: "FamilyValues",
  education_level: "EducationLevel",
  field_of_study: "FieldOfStudy",
  employment_type: "EmploymentType",
  industry: "Industry",
  income_band: "IncomeBand",
  interest: "Interest",
  visibility: "Visibility",
  review_reason: "ReviewReason",
  scope: "Scope",
};

for (const locale of ["en", "ta", "ta-Latn"]) {
  const messages = JSON.parse(
    readFileSync(new URL(`../messages/${locale}.json`, import.meta.url), "utf8"),
  ) as { options: Record<string, Record<string, string>>; profile: { status: Record<string, string> } };

  test(`${locale}: every API option code has a label`, () => {
    for (const [group, schema] of Object.entries(GROUPS)) {
      const codes = openapi.components.schemas[schema]?.enum;
      assert.ok(codes, `OpenAPI schema ${schema} missing`);
      for (const code of codes) {
        assert.ok(messages.options[group]?.[code], `${locale}: options.${group}.${code}`);
      }
    }
  });

  test(`${locale}: every profile status has a label`, () => {
    for (const code of openapi.components.schemas.ProfileStatus!.enum!) {
      assert.ok(messages.profile.status[code], `${locale}: profile.status.${code}`);
    }
  });
}
