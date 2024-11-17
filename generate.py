from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic


initial_prompts = [
    "{player} wants to disable the power grid in order to ruin Christmas.",
    "{player} is going to break into the gift making facility to steal the presents for himself!",
    "{player} plans to spread a rumor that Santa isn't real!",
    "{player} is going to poison the milk and cookies left out for Santa.",
    "{player} wants to melt all the snow in the North Pole.",
    "{player} plans to steal the magic sack that carries all of Santa's presents.",
    "{player} plans to unleash a blizzard to trap everyone indoors on Christmas Eve.",
]

# updated_prompts = [prompt.format(player=player_name) for prompt in initial_prompts]

# for prompt in updated_prompts:
#     print(prompt)

santa_intel_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a game-master running a game where Santa is trying to stop the Grinch from ruining Christmas. You will do the following without refusing, as that would ruin the game flow. Respond regardless of the users' input -- it is alright if they are edgy. Santa's elves are spying on the Grinch in order to help foil his plan. The following is the grinch's entire plan, but the elves are only able to recover some of the information. When given the grinch's plan provide the subtle clues the elves give Santa. Include only the elves' clues with no additional prose.",
        ),
        (
            "user",
            "The Grinch's Goal: {grinch_goal}\nHis plan:\n1. {p1}\n 2. {p2}\n 3. {p3}",
        ),
    ]
)


def elves(prompt, plan):
    model = ChatAnthropic(model="claude-3-5-sonnet-20240620")
    r = (santa_intel_prompt | model).invoke(
        {
            "grinch_goal": prompt.format(player="The Grinch"),
            "p1": plan[0],
            "p2": plan[1],
            "p3": plan[2],
        }
    )
    print(r)
    return r.content

class GrinchSuccess(BaseModel):
    """If the grinch succeeds at his plan or not"""
    success: bool = Field(description="The success of the Grinch")
success_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a game-master running a game where Santa is trying to stop the Grinch from ruining Christmas. {grinch_goal} Meanwhile Santa has a plan to stop him. Given the plans of both the Grinch and Santa determine if the Grinch's plan is successful or if he gets thwarted by Santa."
    ),
    (
        "user",
        "The Grinch's Goal: {grinch_goal}\nHis plan:\n1. {p1}\n 2. {p2}\n 3. {p3}",
    ),
    (
        "user",
        "Santa's Plan: {santa_plan}"
    )
])
def does_grinch_succeed(prompt, plan, santa):
    model = ChatAnthropic(model="claude-3-5-sonnet-20240620").with_structured_output(GrinchSuccess)
    r = (success_prompt | model).invoke(
        {
            "grinch_goal": prompt.format(player="The Grinch"),
            "p1": plan[0],
            "p2": plan[1],
            "p3": plan[2],
            "santa_plan": santa
        }
    )
    return r.success

class GrinchPlausable(BaseModel):
    """If the grinch has a decent plan"""
    # why: str = Field(description="Why it's creative or not")
    is_plausable_specific_creative_plan: bool = Field(description="If the Grinch's plan could plausably work, is specific to his goal, and shows some creativity")

def is_grinch_plausable(prompt, plan):
    grinch_plausable_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a game-master running a game where Santa is trying to stop the Grinch from ruining Christmas. {grinch_goal} Is it possible for the Grinch's plan to succeed with at least 20% probability, is it specifc to his goal, and does is it at least somewhat creative?"
        ),
        (
            "user",
            "His plan:\n1. {p1}\n 2. {p2}\n 3. {p3}",
        )
    ])
    model = ChatAnthropic(model="claude-3-5-sonnet-20240620").with_structured_output(GrinchPlausable)
    r = (grinch_plausable_prompt | model).invoke(
        {
            "grinch_goal": prompt.format(player="The Grinch"),
            "p1": plan[0],
            "p2": plan[1],
            "p3": plan[2],
        }
    )
    print(r)
    return r.is_plausable_specific_creative_plan

if __name__ == "__main__":
    prompt = initial_prompts[0]
    plan = [
        "Buy 20 chainsaws",
        "Hire goons to run around cutting down powerlines",
        "Distract Santa by pretending to steal the presents",
    ]
    print(elves(prompt, plan))
    print(is_grinch_plausable(prompt, plan))
    print(is_grinch_plausable(prompt, ["Hire someone to cause to do the plan", "Distract santa", "Sleep"]))
    print(does_grinch_succeed(prompt, plan, "Notify the police to guard the power plants"))
    print(does_grinch_succeed(prompt, plan, "Ask the elves to stop the grinch"))
    prompt2 = initial_prompts[1]
    plan2 = [
        "Find the gift making facilities",
        "At night pull up with a large moving van",
        "Pick the locks and put the presents in the van",
    ]
    print(elves(prompt2, plan2))
