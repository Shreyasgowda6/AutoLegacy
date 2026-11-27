# AutoLegacy example questions

Use these in the website search box or the terminal chat (`python -m app.cli`). Each search is independent: include the vehicle and problem again when asking a follow-up.

All cases and expert profiles in this project are synthetic demonstration data. Answers describe stored examples, not a diagnosis of an actual vehicle.

## Start with these

1. Why does a Toyota Corolla overheat in slow traffic but run normally at motorway speed?
2. Why does a Volkswagen Golf 1.4 TSI rattle for a few seconds during a cold start?
3. Why did the Renault Clio battery go flat overnight while the cabin lamp stayed on?

## Questions covered by the current JSON knowledge base

| Topic | Example question |
| --- | --- |
| Cold-start noise | What was the confirmed cause of cold-start rattling in the Volkswagen Golf example? |
| Overheating | Which checks identified the cooling fan fault in the Toyota Corolla overheating case? |
| Rough idle | What caused the rough and unstable idle in the Ford Focus example? |
| Hot starting problem | Why did the Opel Astra crank but fail to start when its engine was hot? |
| Vibration | Why did the Renault Clio vibrate at idle when it was in gear? |
| Fuel consumption | What caused excessive fuel consumption on short trips in the Hyundai i30 example? |
| Power loss | What caused the Peugeot 308 to lose power under load and enter limp mode? |
| Oil leakage | Where did the oil leak originate in the Audi A4 example? |
| Exhaust smoke | What caused blue exhaust smoke at start-up in the Ford Fiesta example? |
| Engine shutdown | Why did the Volkswagen Passat randomly shut off while driving? |
| Battery drain | What fixed the overnight battery drain in the Renault Clio cabin-lamp case? |

## Ask about practical expert knowledge

- What common mistakes should be avoided when diagnosing Toyota Corolla overheating in slow traffic?
- What safety precautions were recorded for the Volkswagen Golf cold-start rattle?
- What practical insight helped identify the Ford Focus rough-idle problem?
- Which observations helped confirm the Opel Astra hot-starting fault?
- What lesson was captured from the Audi A4 oil-leak case?

## Test the no-information response

These topics are not covered by the current records:

- I want to buy a new tyre. Which one should I choose?
- How much does a replacement Toyota Corolla cooling fan cost?
- Which workshop near me can repair my car?
- How do I repair a Tesla high-voltage battery?
- What is the best car insurance policy?

Expected behavior: **“No information available.”** The knowledge-gap form should open with the question already included. Submit a short note to test feedback saving, or close the form to return to the answer.

Coverage changes when you add interviews, so these examples may need updating later.

## Questions to ask during an expert interview

Open **Expert Interview**, select an expert, and use these prompts when typing or recording:

1. Which vehicle, model and engine were involved?
2. What symptoms did you observe?
3. When did the problem occur: cold, hot, at idle, under load, or after parking?
4. Which possible causes did you consider?
5. Which checks did you perform, and what did they show?
6. What cause was actually confirmed?
7. What action resolved the problem?
8. What practical lesson would help a junior mechanic?
9. What common mistakes and safety precautions matter?

## Sample interview text or recording script

Select **Dana Brooks** and paste this into **Write interview**, or read it aloud using **Record or upload audio**:

> This is a synthetic demonstration case involving a Honda Civic. The customer reported a squealing noise immediately after the auxiliary drive belt was replaced. The noise occurred during a cold start. We inspected the belt with the engine switched off and found that it was not seated correctly in one pulley groove. The confirmed cause was incorrect belt seating after replacement. Correcting the belt seating resolved the noise. The practical lesson is to verify belt alignment after belt work before assuming that a new component is defective. A common mistake is replacing parts before checking the recent work. Keep hands and tools away from moving belts and follow the vehicle's service procedure.

Choose **Extract knowledge**, review and correct the fields, then select **Add to knowledge base**. Missing details, such as the engine type, should stay empty.

After saving, try:

- Why did the Honda Civic squeal during a cold start after its auxiliary belt was replaced?
- What was the confirmed cause of the Honda Civic belt-noise problem?
- What practical lesson was recorded from the Honda Civic belt replacement case?

The answer should use your newly saved record. These Honda Civic questions are intended for **after** saving the sample; the earlier JSON examples are available immediately.
