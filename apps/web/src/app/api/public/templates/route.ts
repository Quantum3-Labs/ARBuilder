/**
 * Public API for viewing available code templates.
 * Read-only, no authentication required.
 * Provides transparency into available Stylus templates.
 *
 * Usage:
 * GET /api/public/templates - List all available templates
 * GET /api/public/templates?name=counter - Get specific template
 */

import { NextRequest, NextResponse } from "next/server";
import {
  listTemplates,
  COUNTER_TEMPLATE,
  VENDING_MACHINE_TEMPLATE,
  SIMPLE_ERC20_TEMPLATE,
  ACCESS_CONTROL_TEMPLATE,
  type StylusTemplate,
} from "@/lib/templates/stylusTemplates";

// Template names mapping
const TEMPLATES_BY_NAME: Record<string, StylusTemplate> = {
  counter: COUNTER_TEMPLATE,
  "vending-machine": VENDING_MACHINE_TEMPLATE,
  vendingmachine: VENDING_MACHINE_TEMPLATE,
  erc20: SIMPLE_ERC20_TEMPLATE,
  "simple-erc20": SIMPLE_ERC20_TEMPLATE,
  token: SIMPLE_ERC20_TEMPLATE,
  "access-control": ACCESS_CONTROL_TEMPLATE,
  ownable: ACCESS_CONTROL_TEMPLATE,
};

// Public template view (summary without full code)
interface PublicTemplateSummary {
  name: string;
  description: string;
  contractType: string;
  sdkVersion: string;
  features: string[];
}

// Full template view (includes code)
interface PublicTemplateDetail extends PublicTemplateSummary {
  files: {
    libRs: string;
    cargoToml: string;
    mainRs: string;
  };
}

/**
 * GET /api/public/templates
 * List all templates or get a specific template
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const templateName = searchParams.get("name");
    const includeCode = searchParams.get("code") === "true";

    // If specific template requested
    if (templateName) {
      const template = TEMPLATES_BY_NAME[templateName.toLowerCase()];

      if (!template) {
        return NextResponse.json(
          { error: `Template not found: ${templateName}` },
          { status: 404 }
        );
      }

      const detail: PublicTemplateDetail = {
        name: template.name,
        description: template.description,
        contractType: template.contractType,
        sdkVersion: template.sdkVersion,
        features: template.features,
        files: {
          libRs: template.libRs,
          cargoToml: template.cargoToml,
          mainRs: template.mainRs,
        },
      };

      return NextResponse.json({
        status: "ok",
        template: detail,
      });
    }

    // List all templates
    const templates = listTemplates();

    if (includeCode) {
      // Return full templates with code
      const fullTemplates: PublicTemplateDetail[] = templates.map((t) => ({
        name: t.name,
        description: t.description,
        contractType: t.contractType,
        sdkVersion: t.sdkVersion,
        features: t.features,
        files: {
          libRs: t.libRs,
          cargoToml: t.cargoToml,
          mainRs: t.mainRs,
        },
      }));

      return NextResponse.json({
        status: "ok",
        templates: fullTemplates,
        count: fullTemplates.length,
      });
    }

    // Return summaries only (default)
    const summaries: PublicTemplateSummary[] = templates.map((t) => ({
      name: t.name,
      description: t.description,
      contractType: t.contractType,
      sdkVersion: t.sdkVersion,
      features: t.features,
    }));

    return NextResponse.json({
      status: "ok",
      templates: summaries,
      count: summaries.length,
    });
  } catch (error) {
    console.error("Public templates error:", error);
    return NextResponse.json(
      { error: "Failed to fetch templates" },
      { status: 500 }
    );
  }
}
