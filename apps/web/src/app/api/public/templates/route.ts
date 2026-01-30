/**
 * Public API for viewing available code templates.
 * Read-only, no authentication required.
 * Provides transparency into available templates.
 *
 * Usage:
 * GET /api/public/templates - List all available templates
 * GET /api/public/templates?type=stylus - List only Stylus templates
 * GET /api/public/templates?type=sdk - List only SDK templates
 * GET /api/public/templates?name=counter - Get specific Stylus template
 * GET /api/public/templates?name=eth_deposit - Get specific SDK template
 */

import { NextRequest, NextResponse } from "next/server";
import {
  listTemplates as listStylusTemplates,
  COUNTER_TEMPLATE,
  VENDING_MACHINE_TEMPLATE,
  SIMPLE_ERC20_TEMPLATE,
  ACCESS_CONTROL_TEMPLATE,
  type StylusTemplate,
} from "@/lib/templates/stylusTemplates";
import {
  listSdkTemplates,
  SDK_TEMPLATES,
  type SdkTemplate,
} from "@/lib/templates/sdkTemplates";

// Stylus template names mapping
const STYLUS_TEMPLATES_BY_NAME: Record<string, StylusTemplate> = {
  counter: COUNTER_TEMPLATE,
  "vending-machine": VENDING_MACHINE_TEMPLATE,
  vendingmachine: VENDING_MACHINE_TEMPLATE,
  erc20: SIMPLE_ERC20_TEMPLATE,
  "simple-erc20": SIMPLE_ERC20_TEMPLATE,
  token: SIMPLE_ERC20_TEMPLATE,
  "access-control": ACCESS_CONTROL_TEMPLATE,
  ownable: ACCESS_CONTROL_TEMPLATE,
};

// Public Stylus template view
interface PublicStylusTemplate {
  type: "stylus";
  name: string;
  description: string;
  contractType: string;
  sdkVersion: string;
  features: string[];
  files?: {
    libRs: string;
    cargoToml: string;
    mainRs: string;
  };
}

// Public SDK template view
interface PublicSdkTemplate {
  type: "sdk";
  name: string;
  description: string;
  category: string;
  subcategory: string;
  sdkVersion: string;
  dependencies: Record<string, string>;
  envVars: string[];
  notes: string[];
  code?: string;
}

type PublicTemplate = PublicStylusTemplate | PublicSdkTemplate;

/**
 * GET /api/public/templates
 * List all templates or get a specific template
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const templateName = searchParams.get("name");
    const templateType = searchParams.get("type"); // "stylus" | "sdk" | null (all)
    const includeCode = searchParams.get("code") === "true";

    // If specific template requested
    if (templateName) {
      // Check Stylus templates first
      const stylusTemplate = STYLUS_TEMPLATES_BY_NAME[templateName.toLowerCase()];
      if (stylusTemplate) {
        const result: PublicStylusTemplate = {
          type: "stylus",
          name: stylusTemplate.name,
          description: stylusTemplate.description,
          contractType: stylusTemplate.contractType,
          sdkVersion: stylusTemplate.sdkVersion,
          features: stylusTemplate.features,
          files: {
            libRs: stylusTemplate.libRs,
            cargoToml: stylusTemplate.cargoToml,
            mainRs: stylusTemplate.mainRs,
          },
        };
        return NextResponse.json({ status: "ok", template: result });
      }

      // Check SDK templates
      const sdkTemplate = SDK_TEMPLATES[templateName.toLowerCase()];
      if (sdkTemplate) {
        const result: PublicSdkTemplate = {
          type: "sdk",
          name: sdkTemplate.name,
          description: sdkTemplate.description,
          category: sdkTemplate.category,
          subcategory: sdkTemplate.subcategory,
          sdkVersion: sdkTemplate.sdkVersion,
          dependencies: sdkTemplate.dependencies,
          envVars: sdkTemplate.envVars,
          notes: sdkTemplate.notes,
          code: sdkTemplate.code,
        };
        return NextResponse.json({ status: "ok", template: result });
      }

      return NextResponse.json(
        { error: `Template not found: ${templateName}` },
        { status: 404 }
      );
    }

    // Build templates list based on type filter
    const templates: PublicTemplate[] = [];

    // Add Stylus templates
    if (!templateType || templateType === "stylus") {
      const stylusTemplates = listStylusTemplates();
      for (const t of stylusTemplates) {
        const template: PublicStylusTemplate = {
          type: "stylus",
          name: t.name,
          description: t.description,
          contractType: t.contractType,
          sdkVersion: t.sdkVersion,
          features: t.features,
        };
        if (includeCode) {
          template.files = {
            libRs: t.libRs,
            cargoToml: t.cargoToml,
            mainRs: t.mainRs,
          };
        }
        templates.push(template);
      }
    }

    // Add SDK templates
    if (!templateType || templateType === "sdk") {
      const sdkTemplates = listSdkTemplates();
      for (const t of sdkTemplates) {
        const template: PublicSdkTemplate = {
          type: "sdk",
          name: t.name,
          description: t.description,
          category: t.category,
          subcategory: t.subcategory,
          sdkVersion: t.sdkVersion,
          dependencies: t.dependencies,
          envVars: t.envVars,
          notes: t.notes,
        };
        if (includeCode) {
          template.code = t.code;
        }
        templates.push(template);
      }
    }

    return NextResponse.json({
      status: "ok",
      templates,
      count: templates.length,
      stats: {
        stylus: templateType === "sdk" ? 0 : listStylusTemplates().length,
        sdk: templateType === "stylus" ? 0 : listSdkTemplates().length,
      },
    });
  } catch (error) {
    console.error("Public templates error:", error);
    return NextResponse.json(
      { error: "Failed to fetch templates" },
      { status: 500 }
    );
  }
}
