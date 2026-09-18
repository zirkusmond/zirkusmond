import type { Show, ShowEvent } from "#/interfaces/show.ts";
import type { ButtonGroupFieldProps } from "#/components/zirkusmond/form/ButtonGroupField";
import type { CheckboxFieldProps } from "#/components/zirkusmond/form/CheckboxField";
import type { NumberFieldProps } from "#/components/zirkusmond/form/NumberField";
import type { SelectFieldProps } from "#/components/zirkusmond/form/SelectField";
import type { TextFieldProps } from "#/components/zirkusmond/form/TextField";
import i18n from "#/i18n";

export enum FieldType {
  Select = "select",
  Number = "number",
  Checkbox = "checkbox",
  ButtonGroup = "button-group",
  Text = "text",
}

export type DynamicFieldConfig =
  | ({ fieldType: FieldType.Select } & SelectFieldProps)
  | ({ fieldType: FieldType.Number } & NumberFieldProps)
  | ({ fieldType: FieldType.Checkbox } & CheckboxFieldProps)
  | ({ fieldType: FieldType.ButtonGroup; id: string } & ButtonGroupFieldProps)
  | ({ fieldType: FieldType.Text } & TextFieldProps);

interface BuildTicketFieldsParams {
  show: Show;
  selectedEventId: string;
  setSelectedEventId: (id: string) => void;
  attendeeCount: number;
  setAttendeeCount: (count: number) => void;
}

export const buildTicketFields = ({
  show,
  selectedEventId,
  setSelectedEventId,
  attendeeCount,
  setAttendeeCount,
}: BuildTicketFieldsParams): DynamicFieldConfig[] => {
  return [
    {
      fieldType: FieldType.Select,
      id: "event",
      label: i18n.t("form_event"),
      placeholder: i18n.t("form_event_placeholder"),
      value: selectedEventId,
      onChange: setSelectedEventId,
      options: show.upcomingEvents
        .filter((event: ShowEvent) => !event.soldOut)
        .map((event: ShowEvent) => ({
          value: event.id,
          label: event.timeAndDate,
        })),
    },
    {
      fieldType: FieldType.Number,
      id: "attendee-count",
      label: i18n.t("form_tickets"),
      value: attendeeCount,
      onChange: (count) => setAttendeeCount(Math.min(10, Math.max(1, count))),
      min: 1,
      max: 100,
    },
  ];
};

interface BuildNewsletterFieldParams {
  newsletter: boolean;
  setNewsletter: (checked: boolean) => void;
}

export const buildNewsletterField = ({
  newsletter,
  setNewsletter,
}: BuildNewsletterFieldParams): DynamicFieldConfig[] => {
  return [
    {
      fieldType: FieldType.Checkbox,
      id: "newsletter",
      label: i18n.t("form_newsletter"),
      checked: newsletter,
      onChange: setNewsletter,
    },
  ];
};

export const buildPersonalInfoFields = (
  fieldErrors: Record<string, string> = {},
  clearFieldError: (id: string) => void = () => {},
): DynamicFieldConfig[] => {
  return [
    {
      fieldType: FieldType.Text,
      id: "first-name",
      label: i18n.t("form_first_name"),
      name: "firstName",
      required: true,
      error: fieldErrors["first-name"],
      onChange: () => clearFieldError("first-name"),
    },
    {
      fieldType: FieldType.Text,
      id: "last-name",
      label: i18n.t("form_last_name"),
      name: "lastName",
      required: true,
      error: fieldErrors["last-name"],
      onChange: () => clearFieldError("last-name"),
    },
    {
      fieldType: FieldType.Text,
      id: "email",
      label: i18n.t("form_email"),
      name: "email",
      type: "email",
      required: true,
      error: fieldErrors["email"],
      onChange: () => clearFieldError("email"),
    },
  ];
};

export const buildGuestFields = (
  fieldErrors: Record<string, string>,
  clearFieldError: (id: string) => void,
  index: number,
): DynamicFieldConfig[] => {
  return [
    {
      fieldType: FieldType.Text,
      id: `guest-${index}-first-name`,
      label: i18n.t("form_first_name"),
      name: `guest-${index}-first-name`,
      required: true,
      error: fieldErrors[`guest-${index}-first-name`],
      onChange: () => clearFieldError(`guest-${index}-first-name`),
    },
    {
      fieldType: FieldType.Text,
      id: `guest-${index}-last-name`,
      label: i18n.t("form_last_name"),
      name: `guest-${index}-last-name`,
      required: true,
      error: fieldErrors[`guest-${index}-last-name`],
      onChange: () => clearFieldError(`guest-${index}-last-name`),
    },
  ];
};

export const buildPaymentMethodField = (): DynamicFieldConfig[] => {
  return [
    {
      fieldType: FieldType.ButtonGroup,
      id: "payment-method",
      name: "payment-method",
      options: [
        { value: "paypal", label: "PayPal" },
        { value: "stripe", label: "Bank Card" },
      ],
    },
  ];
};
