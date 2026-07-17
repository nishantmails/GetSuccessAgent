"""Generate a realistic sample feedback workbook for demo / dry-run testing."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# (emp_id, name, role, people_manager, account_manager, hr)
_SAMPLE: list[tuple[str, str, str, str, str, str]] = [
    (
        "E001", "Aisha Verma", "Senior Software Engineer",
        "Aisha has been exceptional this year. She delivered the payments migration ahead of "
        "schedule with outstanding quality, mentored three junior engineers, and consistently "
        "took ownership of the hardest design problems. Her proactive leadership in architecture "
        "reviews raised the bar for the whole team. Truly an asset.",
        "Client praised Aisha repeatedly for reliable delivery and excellent communication. "
        "She exceeded every SLA commitment on the account and drove innovative solutions during "
        "the renewal discussions. Strong advocate for the team with the client.",
        "Excellent feedback across the board. Completed all mandatory trainings early, positive "
        "peer feedback, great collaboration scores in the engagement survey. No concerns raised.",
    ),
    (
        "E002", "Rahul Mehta", "Software Engineer",
        "Rahul is a reliable engineer who consistently meets his commitments. Code quality is "
        "good and he improved his testing discipline this year. He collaborates well, though he "
        "can be proactive about volunteering for stretch work.",
        "Delivery on the account has been dependable. Rahul met all sprint commitments; the "
        "client had no complaints. Would like to see more initiative in client-facing demos.",
        "Meets all compliance requirements. Positive peer feedback, no concerns. Solid year.",
    ),
    (
        "E003", "Priya Nair", "QA Lead",
        "Priya leads the QA function with strong ownership. She delivered the automation "
        "framework that cut regression time by 40% and consistently exceeds expectations on "
        "quality metrics. Great mentoring of the QA analysts.",
        "The client values Priya's dedication; defect escape rate improved noticeably. She is "
        "proactive in flagging risks early. Excellent partner to the delivery team.",
        "There is a concern around repeated late logins and two leave-policy exceptions this "
        "year. Performance evidence is strong, but attendance discipline needs improvement.",
    ),
    (
        "E004", "Arjun Singh", "DevOps Engineer",
        "Arjun meets expectations. He keeps the pipelines running reliably and responded well "
        "to incidents. Documentation improved after feedback. He sometimes struggles to "
        "prioritise between project work and operational requests.",
        "Account delivery is stable; no major escalations. Arjun is reliable during releases "
        "though communication during incidents could be more proactive.",
        "Met training requirements late but completed them. Peer feedback is mixed — some "
        "mentions of slow response on chat. Otherwise no issues.",
    ),
    (
        "E005", "Sneha Kulkarni", "Business Analyst",
        "Sneha meets expectations overall. Her requirement documents are consistently high "
        "quality and stakeholders like working with her. Two deliverables were delayed in Q3 "
        "which impacted the sprint plan; she needs improvement in estimation.",
        "The client appreciates Sneha's thorough analysis. There was a delay in the UAT "
        "sign-off documentation that caused a minor escalation, since resolved. Good "
        "collaboration otherwise.",
        "No compliance concerns. Engagement survey shows positive collaboration feedback.",
    ),
    (
        "E006", "Vikram Reddy", "Senior Developer",
        "Vikram is an outstanding technical performer — the strongest coder on the team. He "
        "delivered the inventory optimisation module with excellent quality and consistently "
        "helps others debug complex issues. Great ownership and initiative.",
        "We received a client escalation about Vikram's communication style in status calls — "
        "described as dismissive. Delivery quality is strong but the client relationship "
        "suffered; coaching on client-facing behaviour was suggested.",
        "Positive feedback on technical contribution. One interpersonal complaint was raised "
        "by a peer and closed after mediation. Recommend a communication-skills program.",
    ),
    (
        "E007", "Neha Gupta", "UI Developer",
        "Neha struggled to meet expectations this year. Several deliverables were delayed and "
        "required rework; code review feedback is often not incorporated. She lacks ownership "
        "of defects in her modules. Improvement plan discussions have started.",
        "The client raised concerns about UI quality and missed deadlines on two releases. "
        "Rework cycles impacted the account timeline. Needs significant improvement.",
        "Training completion is pending. Peer feedback mentions inconsistent availability. "
        "A performance improvement plan is being discussed with the manager.",
    ),
    (
        "E008", "Karan Patel", "Support Engineer",
        "Karan's performance is below expectations. Ticket backlog grew under his ownership, "
        "SLA breaches increased, and escalation handling was poor. He lacks the urgency the "
        "role demands despite repeated coaching.",
        "Client complaint logged for delayed resolution of a severity-2 issue. Account metrics "
        "for his queue are the weakest in the team. Immediate improvement required.",
        "Two attendance warnings this year. Training overdue. Overall below expectations; "
        "recommend formal performance management.",
    ),
    (
        "E009", "Divya Iyer", "Data Analyst",
        "Divya exceeds expectations. Her churn-analysis model was excellent and directly "
        "informed the retention strategy. She is proactive, delivers high quality insights, "
        "and improved the team's reporting standards. Great growth this year.",
        "Client praised Divya's dashboard work as innovative and reliable. She consistently "
        "delivers ahead of deadlines and communicates insights clearly. Strong asset to the account.",
        "All compliance items completed early. Very positive peer feedback, especially on "
        "collaboration with the engineering team.",
    ),
    (
        "E010", "Manoj Kumar", "Software Engineer",
        "Manoj meets expectations. He is a steady, reliable contributor who delivers what is "
        "asked with acceptable quality. He should take more initiative in design discussions "
        "and improve unit-test coverage.",
        "Delivery on the account was consistent with no escalations. Manoj is dependable but "
        "rarely goes beyond assigned tasks. Client feedback is neutral to positive.",
        "Compliance complete. No concerns, no standout feedback. Meets expectations.",
    ),
    (
        "E011", "Ananya Rao", "Team Lead",
        "Ananya has grown into a strong team lead. She consistently delivers on commitments, "
        "improved sprint predictability, and mentored two engineers into senior roles. Her "
        "proactive risk management avoided a major release slip. Exceeds expectations.",
        "The client trusts Ananya's leadership; governance calls are well prepared and "
        "action-oriented. Escalations dropped significantly under her watch. Excellent partner.",
        "Ananya is doing fine. Feedback is positive.",
    ),
    (
        "E012", "Rohit Sharma", "Junior Developer",
        "Rohit has improved significantly over the year. Early quality concerns have been "
        "addressed; his last two releases were delivered with good quality. Still needs "
        "improvement in estimating complexity, but the trajectory is positive.",
        "Account feedback is mixed: a delayed delivery in Q1, but reliable performance since. "
        "Client acknowledges his dedication and improvement.",
        "Completed all trainings. Peer feedback notes he is collaborative and eager to learn.",
    ),
]


def create_sample(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"employee_id": eid, "employee_name": name, "employee_role": role,
         "reviewer_role": reviewer, "feedback": text}
        for eid, name, role, pm, am, hr in _SAMPLE
        for reviewer, text in (("People Manager", pm), ("Account Manager", am), ("HR", hr))
    ]
    pd.DataFrame(rows).to_excel(path, index=False)
    print(f"Sample input written to {path} ({len(_SAMPLE)} employees x 3 reviewers)")
    return path


if __name__ == "__main__":
    create_sample(Path(__file__).resolve().parent.parent / "sample_data" / "feedback_input.xlsx")
